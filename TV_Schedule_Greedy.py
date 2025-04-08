from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd 
import visualize

def greedy_scheduler(user_slots, programs_file, tur_dagilimi=False):
    programs = pd.read_excel(programs_file).to_dict(orient='records')
    unique_türler = list({program["Tür"] for program in programs})
    
    # 1. Programları gün ve slotlara göre grupla
    programs_by_day_slot = defaultdict(list)
    for program in programs:
        day = program["Gün"]
        start = datetime.strptime(program["Başlangıç Saati"], "%H:%M")
        end = datetime.strptime(program["Bitiş Saati"], "%H:%M")
        if end < start:
            end += timedelta(days=1)
        program["start"] = start
        program["end"] = end
        
        # Kullanıcı slotlarıyla eşleştirme
        for slot in user_slots:
            if slot["day"] == day:
                slot_start = datetime.strptime(slot["start_time"], "%H:%M")
                slot_end = datetime.strptime(slot["end_time"], "%H:%M")
                if slot_start <= start and end <= slot_end:
                    programs_by_day_slot[(day, slot["start_time"], slot["end_time"])].append(program)
                    break

    # 2. Tür sayaçlarını user_preferences'e göre başlat
    tür_counts = {tür: 0 for tür in unique_türler}
    total_value = 0  # Toplam value değerini tutmak için
    
    scheduled = []
    
    for (day, slot_start, slot_end), programs_in_slot in programs_by_day_slot.items():
        # Değer ve başlangıç saatine göre sırala
        sorted_programs = sorted(
            programs_in_slot, 
            key=lambda x: (x["start"],-x["value"])
        )
        
        selected = []
        last_end = datetime.strptime(slot_start, "%H:%M")
        
        for program in sorted_programs:
            # Kısıt kontrolleri
            valid = True
            
            # 1. Çakışma kontrolü (max 10 dakika)
            for selected_prog in selected:
                overlap_start = max(program["start"], selected_prog["start"])
                overlap_end = min(program["end"], selected_prog["end"])
                if (overlap_end - overlap_start).total_seconds() / 60 > 10:
                    valid = False
                    break
            
            # 2. Bekleme süresi (max 15 dakika)
            wait_time = (program["start"] - last_end).total_seconds() / 60
            if wait_time > 15 and selected:
                valid = False
            
            # 3. Ardışık tür kontrolü (max 2 aynı tür)
            if len(selected) >= 2:
                last_two_tür = [selected[-1]["Tür"], selected[-2]["Tür"]]
                if program["Tür"] == last_two_tür[0] == last_two_tür[1]:
                    valid = False
            
            if tur_dagilimi == True:
                # Tür dağılımı (max %50 ve fark <=5)
                proposed_counts = tür_counts.copy()
                proposed_counts[program["Tür"]] += 1
                total = sum(proposed_counts.values()) + 1
                max_allowed_diff  = max(1, round(total * 0.25))
                print(max_allowed_diff)
                if any(count / total > 0.5 for count in proposed_counts.values()):
                    valid = False
                if max(proposed_counts.values()) - min(proposed_counts.values()) > max_allowed_diff:
                    valid = False
            
            if valid:
                selected.append(program)
                last_end = max(last_end, program["end"])
                tür_counts[program["Tür"]] += 1
                total_value += program["value"]  # Obj değeri için
        
        scheduled.extend(selected)
    
    # Toplam value'yu ve seçilen programları döndür
    print(f"Toplam Değer (Objective Function): {total_value}")
    print(f"Tür Dağılımı: {tür_counts}")
    return scheduled, total_value

# user_slots = [
#     {"day": "Pazartesi", "start_time": "09:00", "end_time": "12:00"},
#     {"day": "Pazartesi", "start_time": "14:00", "end_time": "18:00"},
#     {"day": "Salı", "start_time": "10:00", "end_time": "13:00"},
#     {"day": "Salı", "start_time": "15:00", "end_time": "17:00"},
#     {"day": "Çarşamba", "start_time": "08:00", "end_time": "10:00"},
#     {"day": "Perşembe", "start_time": "19:00", "end_time": "22:00"},
#     {"day": "Cuma", "start_time": "12:00", "end_time": "15:00"},
#     {"day": "Cumartesi", "start_time": "12:00", "end_time": "17:00"},
#     {"day": "Pazar", "start_time": "09:00", "end_time": "15:00"}
# ]

# programs_file = "haftalik_düzenli.xlsx"
# # Kullanım
# scheduled_programs,total_val = greedy_scheduler(user_slots, programs_file)
# visualize.visualize_schedule_interactive(user_slots, [(p, {
#     "day": p["Gün"],
#     "start_time": p["Başlangıç Saati"],
#     "end_time": p["Bitiş Saati"]
# }) for p in scheduled_programs], "greedy")