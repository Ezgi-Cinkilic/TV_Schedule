from ortools.sat.python import cp_model
from datetime import datetime
import pandas as pd
from collections import defaultdict
import visualize

class TvSchedulerCP:
    def __init__(self, user_slots, programs_file, tur_dagilimi=False):
        self.user_slots = user_slots
        self.programs = pd.read_excel(programs_file).to_dict(orient='records')
        self.model = cp_model.CpModel()
        self.program_vars = {}
        self.start_vars = {}
        self.end_vars = {}
        self.selected_programs = []
        self.tur_dagilimi = tur_dagilimi

    def time_to_minutes(self, t):
        return datetime.strptime(t, "%H:%M").hour * 60 + datetime.strptime(t, "%H:%M").minute

    def prepare_data(self):
        user_slots_by_day = defaultdict(list)
        for slot in self.user_slots:
            day = slot["day"]
            start = self.time_to_minutes(slot["start_time"])
            end = self.time_to_minutes(slot["end_time"])
            user_slots_by_day[day].append((start, end))
        
        for program in self.programs:
            program_day = program["Gün"]
            if program_day not in user_slots_by_day:
                continue

            start = self.time_to_minutes(program["Başlangıç Saati"])
            end = self.time_to_minutes(program["Bitiş Saati"])
            
            valid = any(slot_start <= start and end <= slot_end 
                        for slot_start, slot_end in user_slots_by_day[program_day])
            
            if valid:
                program_id = program["id"]
                self.program_vars[program_id] = self.model.NewBoolVar(f'program_{program_id}')
                self.start_vars[program_id] = start
                self.end_vars[program_id] = end
                self.selected_programs.append(program)

    def add_constraints(self):
        selected_programs_by_day = defaultdict(list)
        for program in self.selected_programs:
            selected_programs_by_day[program["Gün"]].append(program)
        
        # 1. ÇAKIŞMA VE ARDIŞIKLIK KISITLARI
        for day, day_programs in selected_programs_by_day.items():
            # Programları başlangıç saatine göre sırala
            day_programs_sorted = sorted(day_programs, key=lambda x: self.start_vars[x["id"]])
            
            # a) Çakışma kısıtı
            for i in range(len(day_programs)):
                for j in range(i+1, len(day_programs)):
                    p1 = day_programs[i]
                    p2 = day_programs[j]
                    self.model.Add(
                        (self.end_vars[p1["id"]] <= self.start_vars[p2["id"]] + 10) |
                        (self.end_vars[p2["id"]] <= self.start_vars[p1["id"]] + 10)
                    ).OnlyEnforceIf(self.program_vars[p1["id"]], self.program_vars[p2["id"]])
            
            # b) Ardışık programlar arası max 15 dakika boşluk
            for i in range(len(day_programs_sorted)-1):
                p1 = day_programs_sorted[i]
                p2 = day_programs_sorted[i+1]
                
                # Seçilen ardışık programlar için boşluk kontrolü
                both_selected = self.model.NewBoolVar(f'both_sel_{p1["id"]}_{p2["id"]}')
                self.model.AddMultiplicationEquality(both_selected, 
                                                  [self.program_vars[p1["id"]], 
                                                   self.program_vars[p2["id"]]])
                
                # Max 15 dakika boşluk kısıtı
                self.model.Add(
                    self.start_vars[p2["id"]] - self.end_vars[p1["id"]] <= 15
                ).OnlyEnforceIf(both_selected)
    
        # 2. ARDIŞIK MAX 2 AYNI TÜR KISITI
        programs_by_day_genre = defaultdict(lambda: defaultdict(list))
        for program in self.selected_programs:
            programs_by_day_genre[program["Gün"]][program["Tür"]].append(program)
        
        for day, genres in programs_by_day_genre.items():
            for genre, programs in genres.items():
                if len(programs) < 3: continue
                        
                timeline = defaultdict(list)
                for program in programs:
                    start = self.start_vars[program["id"]]
                    end = self.end_vars[program["id"]]
                    for minute in range(start, end, 5):
                        timeline[minute].append(program["id"])
                
                consecutive_windows = []
                current_window = []
                    
                for minute in sorted(timeline.keys()):
                    if not current_window or minute - current_window[-1] <= 10:
                        current_window.append(minute)
                    else:
                        if len(current_window) >= 3:
                            consecutive_windows.append(current_window)
                        current_window = [minute]
                    
                if len(current_window) >= 3:
                    consecutive_windows.append(current_window)
                        
                for window in consecutive_windows:
                    window_programs = set()
                    for minute in window:
                        window_programs.update(timeline[minute])
                    
                    if len(window_programs) >= 3:
                        self.model.Add(
                            sum(self.program_vars[pid] for pid in window_programs) <= 2
                        )
        
        # 3. TÜR DAĞILIMI KISITLARI (False)
        if self.tur_dagilimi:
            tür_sayacı = {}
            for tür in set(p["Tür"] for p in self.selected_programs):
                tür_sayacı[tür] = self.model.NewIntVar(0, len(self.selected_programs), f'tür_count_{tür}')
                self.model.Add(
                    tür_sayacı[tür] == sum(self.program_vars[p["id"]] for p in self.selected_programs if p["Tür"] == tür)
                )
            
            tüm_türler = list(tür_sayacı.keys())
            max_tür_farkı = 5
            for i in range(len(tüm_türler)):
                for j in range(i+1, len(tüm_türler)):
                    tür1 = tüm_türler[i]
                    tür2 = tüm_türler[j]
                    self.model.Add(tür_sayacı[tür1] - tür_sayacı[tür2] <= max_tür_farkı)
                    self.model.Add(tür_sayacı[tür2] - tür_sayacı[tür1] <= max_tür_farkı)
            
            total_programs = self.model.NewIntVar(0, len(self.selected_programs), 'total_programs')
            self.model.Add(total_programs == sum(self.program_vars.values()))
            for tür in tüm_türler:
                self.model.Add(2 * tür_sayacı[tür] <= total_programs)

    def solve(self):
        self.prepare_data()
        self.add_constraints()
        self.model.Maximize(sum(self.program_vars[p["id"]] * p["value"] for p in self.selected_programs))
        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)
        
        if status == cp_model.OPTIMAL:
            print("Optimal çözüm bulundu!")
            scheduled_programs = []
            for program in self.selected_programs:
                if solver.Value(self.program_vars[program["id"]]):
                    scheduled_programs.append((
                        program.copy(),
                        {"day": program["Gün"], "start_time": program["Başlangıç Saati"], "end_time": program["Bitiş Saati"]}
                    ))
            total_val = sum(p['value'] for p, _ in scheduled_programs)
            print(f"Toplam Değer: {total_val}")
            #visualize.visualize_schedule_interactive(self.user_slots, scheduled_programs, "cp")
        else:
            print("Çözüm bulunamadı.")
        return scheduled_programs, total_val

def main(user_slots):
    cp_scheduler = TvSchedulerCP(user_slots=user_slots, programs_file="haftalik_düzenli.xlsx")
    cp_solution = cp_scheduler.solve()
    print("Kısıt Programlama Sonuçları:", cp_solution)

if __name__ == "__main__":
    main()
    
    