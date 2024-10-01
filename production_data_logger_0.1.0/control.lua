-- control.lua

-- Event, das jede Sekunde aufgerufen wird
script.on_event(defines.events.on_tick, function(event)
    -- Überprüfe, ob 60 Ticks vergangen sind (etwa 1 Sekunde)
    if event.tick % 60 == 0 then
        local force = game.forces["player"] -- "player" ist die Standard-Fraktion
        local production_stats = force.item_production_statistics

        --Produktion
        --Auslesen der Produktionsdaten von Eisenplatten
        local iron_plate_produced = production_stats.get_input_count("iron-plate")
        --Auslesen der Produktionsdaten von Kupferplatten
        local copper_plate_produced = production_stats.get_input_count("copper-plate")
        --Auslesen der Produktionsdaten von Steinen
        local stone_produced = production_stats.get_input_count("stone")
        --Auslesen der Produktionsdaten von Holz
        local wood_produced = production_stats.get_input_count("wood")
        --Auslesen der Produktionsdaten von Eisenrädern
        local iron_gear_wheel_produced = production_stats.get_input_count("iron-gear-wheel")
        --Auslesen der Produktionsdaten von Elektronischen Schaltkreisen
        local electronic_circuit_produced = production_stats.get_input_count("electronic-circuit")
        --Auslesen der Produktionsdaten von Ziegelsteinen
        local brick_produced = production_stats.get_input_count("stone-brick")
        --Auslesen der Produktionsdaten von Kohle
        local coal_produced = production_stats.get_input_count("coal")
        --Auslesen der Produktionsdaten von den Roten Forschungsflaschen
        local automation_science_pack_produced = production_stats.get_input_count("automation-science-pack")
        --Auslesen der Produktionsdaten von Normaler Munition
        local firearm_magazine_produced = production_stats.get_input_count("firearm-magazine")

        --Verbrauch
        --Auslesen der Verbrauchsdaten von Kupferplatten
        local copper_plate_consumed = production_stats.get_output_count("copper-plate")
        --Auslesen der Verbrauchsdaten von Eisenplatten
        local iron_plate_consumed = production_stats.get_output_count("iron-plate")
        --Auslesen der Verbrauchsdaten von Steinen
        local stone_consumed = production_stats.get_output_count("stone")
        --Auslesen der Verbrauchsdaten von Holz
        local wood_consumed = production_stats.get_output_count("wood")
        --Auslesen der Verbrauchsdaten von Eisenrädern
        local iron_gear_wheel_consumed = production_stats.get_output_count("iron-gear-wheel")
        --Auslesen der Verbrauchsdaten von Elektronischen Schaltkreisen
        local electronic_circuit_consumed = production_stats.get_output_count("electronic-circuit")
        --Auslesen der Verbrauchsdaten von Ziegelsteinen
        local brick_consumed = production_stats.get_output_count("stone-brick")
        --Auslesen der Verbrauchsdaten von Kohle
        local coal_consumed = production_stats.get_output_count("coal")
        --Auslesen der Verbrauchsdaten von den Roten Forschungsflaschen
        local automation_science_pack_consumed = production_stats.get_output_count("automation-science-pack")
        --Auslesen der Verbrauchsdaten von Normaler Munition
        local firearm_magazine_consumed = production_stats.get_output_count("firearm-magazine")

        --Verfügbar: geht leider nicht so sondern nur das Inventar
        -- Auslesen der verfügbaren Eisenplatten
        --local iron_plate_available = game.players[1].get_main_inventory().get_item_count("iron-plate")

        -- Aktuelle Spielzeit in Ticks
        local tick = game.tick
        local seconds = tick / 60
        local minutes = math.floor(seconds / 60)
        local hours = math.floor(minutes / 60)
        seconds = seconds % 60
        minutes = minutes % 60

        -- Formatierte Spielzeit
        local time_string = string.format("%02d:%02d:%02d", hours, minutes, seconds)

        -- Speichern in eine Datei (muss später von einem externen Programm ausgelesen werden)
        --Produktion:
        game.write_file("production_log.txt", time_string .. " - Eisenplatten produziert: " .. iron_plate_produced .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Kupferplatten produziert: " .. copper_plate_produced .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Steine produziert: " .. stone_produced .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Holz produziert: " .. wood_produced .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Eisenräder produziert: " .. iron_gear_wheel_produced .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Elektronische Schaltkreise produziert: " .. electronic_circuit_produced .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Ziegelsteine produziert: " .. brick_produced .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Kohle produziert: " .. coal_produced .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Wissenschaftspakete für Automatisierung produziert: " .. automation_science_pack_produced .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Schusswaffen-Munition produziert: " .. firearm_magazine_produced .. "\n", true)

        --Verbrauch:
        game.write_file("production_log.txt", time_string .. " - Kupferplatten verbraucht: " .. copper_plate_consumed .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Eisenplatten verbraucht: " .. iron_plate_consumed .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Steine verbraucht: " .. stone_consumed .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Holz verbraucht: " .. wood_consumed .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Eisenräder verbraucht: " .. iron_gear_wheel_consumed .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Elektronische Schaltkreise verbraucht: " .. electronic_circuit_consumed .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Ziegelsteine verbraucht: " .. brick_consumed .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Kohle verbraucht: " .. coal_consumed .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Wissenschaftspakete für Automatisierung verbraucht: " .. automation_science_pack_consumed .. "\n", true)
        game.write_file("production_log.txt", time_string .. " - Schusswaffen-Munition verbraucht: " .. firearm_magazine_consumed .. "\n", true)

        --Verfügbar: geht leider nicht so sondern nur das Inventar
        --game.write_file("production_log.txt", time_string .. " - Eisenplatten verfügbar: " .. iron_plate_available .. "\n", true)

        --Aber hier für Exeltabelle

        -- Berechnung der verfügbaren Summe

        if event.tick == 0 then
            local header = "Zeit,Produziert Eisen,Verbraucht Eisen\n"
            game.write_file("production_data.csv", header, false)
        end
        
        -- Produktion und Verbrauch in CSV-Format speichern
        local csv_line = string.format("%s,  Produziert Eisen: %d,  Verbraucht Eisen: %d\n", time_string, iron_plate_produced, iron_plate_consumed)
        game.write_file("production_data.csv", csv_line, true)
        

        local iron_plate_available = iron_plate_produced - iron_plate_consumed

        if event.tick == 0 then
            local header = "Zeit,Verfügbare Eisenplatten\n"
            game.write_file("production_data.csv", header, false)
        end
        
        -- Verfügbare Summe in CSV-Format speichern
        local csv_line = string.format("%s,  Verfügbar: %d Eisenplatten\n", time_string, iron_plate_available)
        game.write_file("production_data.csv", csv_line, true)


    end
end)
