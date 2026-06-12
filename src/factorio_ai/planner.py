from __future__ import annotations

from typing import Any

from .models import (
    PlannerDecision,
    craftable_count,
    distance,
    entities_named,
    entity_item_count,
    inventory_count,
    nearest_entity,
    nearest_resource,
    player_position,
    total_item_count,
)


EAST = 2


class IronPlateSkill:
    """Rule-based early-game skill that bootstraps iron plate production."""

    def __init__(self, target_count: int = 10) -> None:
        self.target_count = target_count

    def next_action(self, observation: dict[str, Any]) -> PlannerDecision:
        iron_total = total_item_count(observation, "iron-plate")
        if iron_total >= self.target_count:
            return PlannerDecision(None, f"iron plate target reached: {iron_total}/{self.target_count}", done=True)

        furnace = nearest_entity(observation, "stone-furnace")
        drill = nearest_entity(observation, "burner-mining-drill")
        player = player_position(observation)

        if furnace and entity_item_count(furnace, "iron-plate") > 0:
            furnace_pos = _position(furnace)
            if distance(player, furnace_pos) > 20:
                return PlannerDecision(
                    {"type": "move_to", "position": furnace_pos},
                    "move near furnace to take produced iron plates",
                )
            return PlannerDecision(
                {
                    "type": "take",
                    "item": "iron-plate",
                    "count": min(50, entity_item_count(furnace, "iron-plate")),
                    "unit_number": furnace.get("unit_number"),
                    "name": "stone-furnace",
                    "position": _position(furnace),
                },
                "take produced iron plates from furnace",
            )

        if inventory_count(observation, "coal") < 6:
            coal = nearest_resource(observation, "coal")
            if coal is None:
                return PlannerDecision(None, "cannot find nearby coal")
            return self._mine_resource(player, coal, "coal", 8)

        if furnace is None and inventory_count(observation, "stone-furnace") <= 0:
            if craftable_count(observation, "stone-furnace") > 0:
                return PlannerDecision(
                    {"type": "craft", "recipe": "stone-furnace", "count": 1},
                    "craft stone furnace",
                )
            stone = nearest_resource(observation, "stone")
            if stone is not None:
                return self._mine_resource(player, stone, "stone", 8)

        if drill is None and inventory_count(observation, "burner-mining-drill") <= 0:
            if craftable_count(observation, "burner-mining-drill") > 0:
                return PlannerDecision(
                    {"type": "craft", "recipe": "burner-mining-drill", "count": 1},
                    "craft burner mining drill",
                )
            return PlannerDecision(None, "missing burner mining drill and cannot craft it from current inventory")

        if drill is None:
            iron = nearest_resource(observation, "iron-ore")
            if iron is None:
                return PlannerDecision(None, "cannot find nearby iron ore")
            iron_pos = _position(iron)
            stand_pos = _stand_position(iron_pos)
            if distance(player, stand_pos) > 20:
                return PlannerDecision(
                    {"type": "move_to", "position": stand_pos},
                    "move near iron ore before placing burner mining drill",
                )
            return PlannerDecision(
                {
                    "type": "build",
                    "name": "burner-mining-drill",
                    "position": iron_pos,
                    "direction": EAST,
                    "allow_nearby": True,
                },
                "place burner mining drill on iron ore",
            )

        if furnace is None:
            drill_pos = _position(drill)
            furnace_pos = {"x": drill_pos["x"] + 3, "y": drill_pos["y"]}
            stand_pos = _stand_position(furnace_pos)
            if distance(player, stand_pos) > 20:
                return PlannerDecision(
                    {"type": "move_to", "position": stand_pos},
                    "move near drill before placing furnace",
                )
            return PlannerDecision(
                {
                    "type": "build",
                    "name": "stone-furnace",
                    "position": furnace_pos,
                    "allow_nearby": True,
                },
                "place furnace at drill output",
            )

        if furnace and entity_item_count(furnace, "iron-ore") < 5 and inventory_count(observation, "iron-ore") <= 0:
            iron = nearest_resource(observation, "iron-ore")
            if iron is None:
                return PlannerDecision(None, "cannot find nearby iron ore for furnace input")
            return self._mine_resource(player, iron, "iron-ore", 10)

        if furnace and inventory_count(observation, "iron-ore") > 0 and entity_item_count(furnace, "iron-ore") < 5:
            furnace_pos = _position(furnace)
            if distance(player, furnace_pos) > 20:
                return PlannerDecision(
                    {"type": "move_to", "position": furnace_pos},
                    "move near furnace to insert iron ore",
                )
            return PlannerDecision(
                {
                    "type": "insert",
                    "item": "iron-ore",
                    "count": min(10, inventory_count(observation, "iron-ore")),
                    "unit_number": furnace.get("unit_number"),
                    "name": "stone-furnace",
                    "position": _position(furnace),
                },
                "insert iron ore into furnace",
            )

        if drill and inventory_count(observation, "coal") > 0 and entity_item_count(drill, "coal") < 3:
            drill_pos = _position(drill)
            if distance(player, drill_pos) > 20:
                return PlannerDecision(
                    {"type": "move_to", "position": drill_pos},
                    "move near drill to insert coal",
                )
            return PlannerDecision(
                {
                    "type": "insert",
                    "item": "coal",
                    "count": min(5, inventory_count(observation, "coal")),
                    "unit_number": drill.get("unit_number"),
                    "name": "burner-mining-drill",
                    "position": _position(drill),
                },
                "fuel burner mining drill",
            )

        if furnace and inventory_count(observation, "coal") > 0 and entity_item_count(furnace, "coal") < 3:
            furnace_pos = _position(furnace)
            if distance(player, furnace_pos) > 20:
                return PlannerDecision(
                    {"type": "move_to", "position": furnace_pos},
                    "move near furnace to insert coal",
                )
            return PlannerDecision(
                {
                    "type": "insert",
                    "item": "coal",
                    "count": min(5, inventory_count(observation, "coal")),
                    "unit_number": furnace.get("unit_number"),
                    "name": "stone-furnace",
                    "position": _position(furnace),
                },
                "fuel stone furnace",
            )

        return PlannerDecision(
            {"type": "wait", "ticks": 300},
            "wait for miner/furnace production",
        )

    def _mine_resource(
        self,
        player: dict[str, float],
        resource: dict[str, Any],
        name: str,
        count: int,
    ) -> PlannerDecision:
        pos = _position(resource)
        if distance(player, pos) > 8:
            return PlannerDecision(
                {"type": "move_to", "position": pos},
                f"move near {name}",
            )
        return PlannerDecision(
            {
                "type": "mine",
                "target": "resource",
                "name": name,
                "near": pos,
                "count": count,
            },
            f"mine {name}",
        )


class AutomationScienceSkill:
    """Second milestone: produce automation science packs after iron smelting works."""

    def __init__(self, target_count: int = 5, iron_plate_floor: int = 10) -> None:
        self.target_count = target_count
        self.iron_plate_floor = iron_plate_floor
        self.iron_skill = IronPlateSkill(iron_plate_floor)

    def next_action(self, observation: dict[str, Any]) -> PlannerDecision:
        science_total = total_item_count(observation, "automation-science-pack")
        if science_total >= self.target_count:
            return PlannerDecision(
                None,
                f"automation science target reached: {science_total}/{self.target_count}",
                done=True,
            )

        if total_item_count(observation, "iron-plate") < self.iron_plate_floor:
            decision = self.iron_skill.next_action(observation)
            if decision.action is not None:
                return decision

        player = player_position(observation)
        copper_plate_inventory = inventory_count(observation, "copper-plate")
        gear_total = inventory_count(observation, "iron-gear-wheel")
        science_needed = self.target_count - science_total

        if craftable_count(observation, "automation-science-pack") > 0:
            return PlannerDecision(
                {
                    "type": "craft",
                    "recipe": "automation-science-pack",
                    "count": min(science_needed, craftable_count(observation, "automation-science-pack")),
                },
                "craft automation science packs",
            )

        if gear_total < science_needed and craftable_count(observation, "iron-gear-wheel") > 0:
            return PlannerDecision(
                {
                    "type": "craft",
                    "recipe": "iron-gear-wheel",
                    "count": min(science_needed - gear_total, craftable_count(observation, "iron-gear-wheel")),
                },
                "craft iron gear wheels for automation science",
            )

        if copper_plate_inventory < science_needed:
            decision = self._produce_copper_plate(observation, player, science_needed)
            if decision is not None:
                return decision

        if gear_total < science_needed:
            return PlannerDecision(None, "missing iron gear wheels and cannot craft them")

        return PlannerDecision(
            {"type": "wait", "ticks": 120},
            "wait before rechecking automation science prerequisites",
        )

    def _produce_copper_plate(
        self,
        observation: dict[str, Any],
        player: dict[str, float],
        science_needed: int,
    ) -> PlannerDecision | None:
        copper_furnace = _select_copper_furnace(observation)
        copper = nearest_resource(observation, "copper-ore")
        if copper is None:
            return PlannerDecision(None, "cannot find nearby copper ore")

        if inventory_count(observation, "coal") < 6:
            coal = nearest_resource(observation, "coal")
            if coal is None:
                return PlannerDecision(None, "cannot find nearby coal for copper smelting")
            return self.iron_skill._mine_resource(player, coal, "coal", 8)

        if copper_furnace is None:
            furnaces = entities_named(observation, "stone-furnace")
            if len(furnaces) < 2:
                if inventory_count(observation, "stone-furnace") <= 0:
                    if craftable_count(observation, "stone-furnace") > 0:
                        return PlannerDecision(
                            {"type": "craft", "recipe": "stone-furnace", "count": 1},
                            "craft second stone furnace for copper smelting",
                        )
                    stone = nearest_resource(observation, "stone")
                    if stone is None:
                        return PlannerDecision(None, "cannot find stone for second furnace")
                    return self.iron_skill._mine_resource(player, stone, "stone", 8)
                copper_pos = _position(copper)
                furnace_pos = {"x": copper_pos["x"] + 3, "y": copper_pos["y"]}
                if distance(player, furnace_pos) > 20:
                    return PlannerDecision(
                        {"type": "move_to", "position": furnace_pos},
                        "move near copper patch before placing copper furnace",
                    )
                return PlannerDecision(
                    {
                        "type": "build",
                        "name": "stone-furnace",
                        "position": furnace_pos,
                        "allow_nearby": True,
                    },
                    "place second furnace for copper smelting",
                )
            copper_furnace = _nearest_to(furnaces, _position(copper))

        if copper_furnace and entity_item_count(copper_furnace, "copper-plate") > 0:
            furnace_pos = _position(copper_furnace)
            if distance(player, furnace_pos) > 20:
                return PlannerDecision(
                    {"type": "move_to", "position": furnace_pos},
                    "move near copper furnace to take copper plates",
                )
            return PlannerDecision(
                {
                    "type": "take",
                    "item": "copper-plate",
                    "count": min(50, entity_item_count(copper_furnace, "copper-plate")),
                    "unit_number": copper_furnace.get("unit_number"),
                    "name": "stone-furnace",
                    "position": furnace_pos,
                },
                "take produced copper plates from furnace",
            )

        if inventory_count(observation, "copper-ore") <= 0:
            return self.iron_skill._mine_resource(player, copper, "copper-ore", max(8, science_needed))

        furnace_pos = _position(copper_furnace)
        if entity_item_count(copper_furnace, "copper-ore") < science_needed:
            if distance(player, furnace_pos) > 20:
                return PlannerDecision(
                    {"type": "move_to", "position": furnace_pos},
                    "move near copper furnace to insert copper ore",
                )
            return PlannerDecision(
                {
                    "type": "insert",
                    "item": "copper-ore",
                    "count": min(max(8, science_needed), inventory_count(observation, "copper-ore")),
                    "unit_number": copper_furnace.get("unit_number"),
                    "name": "stone-furnace",
                    "position": furnace_pos,
                },
                "insert copper ore into copper furnace",
            )

        if entity_item_count(copper_furnace, "coal") < 3:
            if distance(player, furnace_pos) > 20:
                return PlannerDecision(
                    {"type": "move_to", "position": furnace_pos},
                    "move near copper furnace to insert coal",
                )
            return PlannerDecision(
                {
                    "type": "insert",
                    "item": "coal",
                    "count": min(5, inventory_count(observation, "coal")),
                    "unit_number": copper_furnace.get("unit_number"),
                    "name": "stone-furnace",
                    "position": furnace_pos,
                },
                "fuel copper furnace",
            )

        return PlannerDecision(
            {"type": "wait", "ticks": 300},
            "wait for copper plates",
        )


def _position(entity: dict[str, Any]) -> dict[str, float]:
    position = entity.get("position") if isinstance(entity.get("position"), dict) else {}
    return {
        "x": float(position.get("x") or 0.0),
        "y": float(position.get("y") or 0.0),
    }


def _stand_position(target: dict[str, float], offset: float = 2.0) -> dict[str, float]:
    return {"x": float(target["x"]) + offset, "y": float(target["y"])}


def _select_copper_furnace(observation: dict[str, Any]) -> dict[str, Any] | None:
    furnaces = entities_named(observation, "stone-furnace")
    for item in furnaces:
        if entity_item_count(item, "copper-plate") > 0 or entity_item_count(item, "copper-ore") > 0:
            return item
    copper = nearest_resource(observation, "copper-ore")
    if copper is None or len(furnaces) < 2:
        return None
    iron_busy = [
        item
        for item in furnaces
        if entity_item_count(item, "iron-plate") > 0 or entity_item_count(item, "iron-ore") > 0
    ]
    candidates = [item for item in furnaces if item not in iron_busy] or furnaces
    return _nearest_to(candidates, _position(copper))


def _nearest_to(entities: list[dict[str, Any]], position: dict[str, float]) -> dict[str, Any] | None:
    if not entities:
        return None
    return min(entities, key=lambda item: distance(_position(item), position))
