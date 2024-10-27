-- control.lua

-- Event, das jede Sekunde aufgerufen wird
script.on_event(defines.events.on_tick, function(event)
    -- Überprüfe, ob 60 Ticks vergangen sind (etwa 1 Sekunde)
    if event.tick % 60 == 0 then
        local force = game.forces["player"] -- "player" ist die Standard-Fraktion
        local production_stats = force.get_item_production_statistics(1)

        local items = {
            "advanced-circuit",
            "battery",
            "coal",
            "concrete",
            "copper-cable",
            "copper-ore",
            "copper-plate",
            "electronic-circuit",
            "engine-unit",
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
            "flying-robot-frame",
            "inserter",
            "iron-chest",
            "iron-gear-wheel",
            "iron-ore",
            "iron-plate",
            "iron-stick",
            "linked-belt",
            "linked-chest",
            "loader",
            "logistic-robot",
            "long-handed-inserter",
            "nuclear-fuel",
            "pipe",
            "pipe-to-ground",
            "plastic-bar",
            "rocket-fuel",
            "rocket-part",
            "solar-panel",
            "solid-fuel",
            "splitter",
            "steel-chest",
            "steel-plate",
            "stone",
            "stone-brick",
            "storage-tank",
            "sulfur",
            "transport-belt",
            "underground-belt",
            "uranium-235",
            "uranium-238",
            "uranium-fuel-cell",
            "uranium-ore",
            "wood",
            "wooden-chest"
        }
        
        for i = 1, #items do
            local item = items[i]
            local produced = production_stats.get_flow_count{name=item, category="input", precision_index=defines.flow_precision_index.one_minute}
            local used = production_stats.get_flow_count{name=item, category="output", precision_index=defines.flow_precision_index.one_minute}
            
            -- Schreibe die Produktionsdaten in die Datei
            helpers.write_file("production_log.txt", "t:" .. event.tick .. " " .. item .. "= i:" .. produced .. " o:" .. used .. "\n", true)
        end
        
    end
end)
