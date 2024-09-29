-- control.lua

-- Event, das jede Sekunde aufgerufen wird
script.on_event(defines.events.on_tick, function(event)
    -- Überprüfe, ob 60 Ticks vergangen sind (etwa 1 Sekunde)
    if event.tick % 600 == 0 then
        local force = game.forces["player"] -- "player" ist die Standard-Fraktion
        local production_stats = force.item_production_statistics

        -- Beispiel: Auslesen der Produktionsdaten von Eisenplatten
        local iron_plate_produced = production_stats.get_flow_count{name="iron-plate", input=true, precision_index=defines.flow_precision_index.one_minute}
        local iron_plate_used = production_stats.get_flow_count{name="iron-plate", input=false, precision_index=defines.flow_precision_index.one_minute}

        local copper_plate_produced = production_stats.get_flow_count{name="copper-plate", input=true, precision_index=defines.flow_precision_index.one_minute}
        local copper_plate_used = production_stats.get_flow_count{name="copper-plate", input=false, precision_index=defines.flow_precision_index.one_minute}

        -- Speichern in eine Datei (muss später von einem externen Programm ausgelesen werden)
        game.write_file("production_log.txt", "t:" .. event.tick .. " Ironplates= i:" .. iron_plate_produced .. " o:" .. iron_plate_used .. "\n", true)
        game.write_file("production_log.txt", "t:" .. event.tick .. " Copperlates= i:" .. copper_plate_produced .. " o:" .. copper_plate_used .. "\n", true)
    end
end)
