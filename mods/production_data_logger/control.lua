-- control.lua

script.on_event(defines.events.on_tick, function(event)
    if event.tick % 300 == 0 then
        local force = game.forces["player"] -- "player" ist die Standard-Fraktion
        local production_stats = force.get_item_production_statistics(1)

local items = {"coal"}
        
        for i = 1, #items do
            local item = items[i]
            local produced = production_stats.get_flow_count{name=item, category="input", precision_index=defines.flow_precision_index.one_minute}
            local used = production_stats.get_flow_count{name=item, category="output", precision_index=defines.flow_precision_index.one_minute}
            
            -- Schreibe die Produktionsdaten in die Datei
            helpers.write_file("production_log.txt", "t:" .. event.tick .. " " .. item .. "= i:" .. produced .. " o:" .. used .. "\n", true)

        end
        
    end
end)
