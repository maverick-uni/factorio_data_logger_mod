-- control.lua

-- Event, das jede Sekunde aufgerufen wird
script.on_event(defines.events.on_tick, function(event)
    -- Überprüfe, ob 60 Ticks vergangen sind (etwa 1 Sekunde)
    if event.tick % 600 == 0 then
        local force = game.forces["player"] -- "player" ist die Standard-Fraktion
        local production_stats = force.item_production_statistics

        local items = {
            "accumulator",
            "advanced-circuit",
            "arithmetic-combinator",
            "artillery-turret",
            "assembling-machine-1",
            "assembling-machine-2",
            "assembling-machine-3",
            "battery",
            "battery-equipment",
            "battery-mk2-equipment",
            "beacon",
            "belt-immunity-equipment",
            "big-electric-pole",
            "boiler",
            "burner-generator",
            "burner-inserter",
            "burner-mining-drill",
            "centrifuge",
            "chemical-plant",
            "coal",
            "coin",
            "concrete",
            "constant-combinator",
            "construction-robot",
            "copper-cable",
            "copper-ore",
            "copper-plate",
            "crude-oil-barrel",
            "decider-combinator",
            "discharge-defense-equipment",
            "electric-energy-interface",
            "electric-engine-unit",
            "electric-furnace",
            "electric-mining-drill",
            "electronic-circuit",
            "empty-barrel",
            "energy-shield-equipment",
            "energy-shield-mk2-equipment",
            "engine-unit",
            "exoskeleton-equipment",
            "explosives",
            "express-loader",
            "express-splitter",
            "express-transport-belt",
            "express-underground-belt",
            "fast-inserter",
            "fast-loader",
            "fast-splitter",
            "fast-transport-belt",
            "fast-underground-belt",
            "filter-inserter",
            "flamethrower-turret",
            "flying-robot-frame",
            "fusion-reactor-equipment",
            "gate",
            "green-wire",
            "gun-turret",
            "hazard-concrete",
            "heat-exchanger",
            "heat-interface",
            "heat-pipe",
            "heavy-oil-barrel",
            "infinity-chest",
            "infinity-pipe",
            "inserter",
            "iron-chest",
            "iron-gear-wheel",
            "iron-ore",
            "iron-plate",
            "iron-stick",
            "item-unknown",
            "lab",
            "land-mine",
            "landfill",
            "laser-turret",
            "light-oil-barrel",
            "linked-belt",
            "linked-chest",
            "loader",
            "logistic-chest-active-provider",
            "logistic-chest-buffer",
            "logistic-chest-passive-provider",
            "logistic-chest-requester",
            "logistic-chest-storage",
            "logistic-robot",
            "long-handed-inserter",
            "low-density-structure",
            "lubricant-barrel",
            "medium-electric-pole",
            "night-vision-equipment",
            "nuclear-fuel",
            "nuclear-reactor",
            "offshore-pump",
            "oil-refinery",
            "personal-laser-defense-equipment",
            "personal-roboport-equipment",
            "personal-roboport-mk2-equipment",
            "petroleum-gas-barrel",
            "pipe",
            "pipe-to-ground",
            "plastic-bar",
            "player-port",
            "power-switch",
            "processing-unit",
            "programmable-speaker",
            "pump",
            "pumpjack",
            "radar",
            "rail-chain-signal",
            "rail-signal",
            "red-wire",
            "refined-concrete",
            "refined-hazard-concrete",
            "roboport",
            "rocket-control-unit",
            "rocket-fuel",
            "rocket-part",
            "rocket-silo",
            "satellite",
            "simple-entity-with-force",
            "simple-entity-with-owner",
            "small-electric-pole",
            "small-lamp",
            "solar-panel",
            "solar-panel-equipment",
            "solid-fuel",
            "splitter",
            "stack-filter-inserter",
            "stack-inserter",
            "steam-engine",
            "steam-turbine",
            "steel-chest",
            "steel-furnace",
            "steel-plate",
            "stone",
            "stone-brick",
            "stone-furnace",
            "stone-wall",
            "storage-tank",
            "substation",
            "sulfur",
            "sulfuric-acid-barrel",
            "train-stop",
            "transport-belt",
            "underground-belt",
            "uranium-235",
            "uranium-238",
            "uranium-fuel-cell",
            "uranium-ore",
            "used-up-uranium-fuel-cell",
            "water-barrel",
            "wood",
            "wooden-chest"
        }
        
        for _, item in ipairs(items) do
            local produced = production_stats.get_flow_count{name=item, input=true, precision_index=defines.flow_precision_index.one_minute}
            local used = production_stats.get_flow_count{name=item, input=false, precision_index=defines.flow_precision_index.one_minute}
            local available = produced - used  -- Berechnung des verfügbaren Bestands
            game.write_file("production_log.txt", "t:" .. event.tick .. " " .. item .. "= i:" .. produced .. " o:" .. used .. " a:" .. available .. "\n", true)
        end
    end
end)
