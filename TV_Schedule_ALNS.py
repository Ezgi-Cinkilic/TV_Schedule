# -*- coding: utf-8 -*-
"""
Created on Mon Apr  7 19:10:52 2025

@author: ASUS
"""

import random
import math
import copy
from datetime import datetime, timedelta
import pandas as pd
import TV_Schedule_Greedy
import visualize

class TvSchedulerALNS:
    def __init__(self, user_slots, programs_file, initial_solution=None):
        self.user_slots = user_slots
        self.programs_file = programs_file
        self.programs = pd.read_excel(programs_file).to_dict(orient='records')
        self.unique_türler = list({program["Tür"] for program in self.programs})
        
        for program in self.programs:
            program["start"] = datetime.strptime(program["Başlangıç Saati"], "%H:%M")
            program["end"] = datetime.strptime(program["Bitiş Saati"], "%H:%M")
            if program["end"] < program["start"]:
                program["end"] += timedelta(days=1)
        
        self.current_solution, self.current_value = initial_solution if initial_solution else self.greedy_solution()
        self.best_solution = copy.deepcopy(self.current_solution)
        self.best_value = self.current_value
        
        # ALNS parameters
        self.max_iterations = 1000
        self.max_no_improve = 50
        self.temperature = 1.0
        self.cooling_rate = 0.995
        self.destroy_rates = [0.1, 0.2, 0.3]  # Small, medium, large destruction
        self.repair_weights = [1, 1, 1]  # Weights for different repair operators
        self.destroy_weights = [1, 1, 1]  # Weights for different destroy operators
        
    def greedy_solution(self, tur_dagilimi=False):
        """Your original greedy scheduler as a method"""
        return TV_Schedule_Greedy.greedy_scheduler(self.user_slots, self.programs_file)
    
    def objective_function(self, solution):
        """Calculate total value of the solution"""
        return sum(program["value"] for program in solution)
    
    def is_valid_solution(self, solution):
        """Check if solution meets all constraints"""
        if not solution:
            return True
        
        tür_sequence = []
        
        # Programları gün ve başlangıç saatine göre sırala
        sorted_solution = sorted(solution, key=lambda x: (x["Gün"], x["start"]))
        
        for i in range(len(sorted_solution)):
            current_program = sorted_solution[i]
            tür_sequence.append(current_program["Tür"])
            
            # 1. Ardışık tür kontrolü (3 aynı tür üst üste olmamalı)
            if len(tür_sequence) >= 3:
                if tür_sequence[-3] == tür_sequence[-2] == tür_sequence[-1]:
                    return False
            
            # 2. Çakışma kontrolü (max 10 dakika)
            for j in range(i+1, len(sorted_solution)):
                next_program = sorted_solution[j]
                
                # Aynı gündeki programları kontrol et
                if current_program["Gün"] == next_program["Gün"]:
                    overlap_start = max(current_program["start"], next_program["start"])
                    overlap_end = min(current_program["end"], next_program["end"])
                    overlap_minutes = (overlap_end - overlap_start).total_seconds() / 60
                    
                    if overlap_minutes > 10:
                        return False
            
            # 3. Bekleme süresi kontrolü (max 15 dakika)
            if i > 0 and current_program["Gün"] == sorted_solution[i-1]["Gün"]:
                prev_end = sorted_solution[i-1]["end"]
                current_start = current_program["start"]
                wait_minutes = (current_start - prev_end).total_seconds() / 60
                
                if wait_minutes > 15:
                    return False
                    
        return True
    def destroy_random(self, solution, destruction_rate):
        """Randomly remove programs from solution"""
        destroyed = copy.deepcopy(solution)
        n_to_remove = int(len(destroyed) * destruction_rate)
        removed = []
        
        for _ in range(n_to_remove):
            if not destroyed:
                break
            idx = random.randint(0, len(destroyed)-1)
            removed.append(destroyed.pop(idx))
            
        return destroyed, removed
    
    def destroy_weakest(self, solution, destruction_rate):
        """Remove programs with lowest value"""
        destroyed = copy.deepcopy(solution)
        n_to_remove = int(len(destroyed) * destruction_rate)
        removed = []
        
        if n_to_remove >= len(destroyed):
            removed = destroyed
            destroyed = []
        else:
            destroyed.sort(key=lambda x: x["value"])
            removed = destroyed[:n_to_remove]
            destroyed = destroyed[n_to_remove:]
            
        return destroyed, removed
    
    def destroy_cluster(self, solution, destruction_rate):
        """Remove programs from the same time cluster"""
        destroyed = copy.deepcopy(solution)
        n_to_remove = int(len(destroyed) * destruction_rate)
        removed = []
        
        if not destroyed:
            return destroyed, removed
        
        cluster_day = random.choice(list(set(p["Gün"] for p in destroyed)))
        cluster_programs = [p for p in destroyed if p["Gün"] == cluster_day]
        
        if len(cluster_programs) > n_to_remove:
            removed = random.sample(cluster_programs, n_to_remove)
        else:
            removed = cluster_programs
            
        destroyed = [p for p in destroyed if p not in removed]
        return destroyed, removed
    
    def repair_greedy(self, partial_solution, removed):
        """Greedy repair similar to initial solution"""
        candidate = copy.deepcopy(partial_solution)
        remaining_programs = [p for p in self.programs if p not in candidate]
        
        all_candidates = removed + remaining_programs
        all_candidates.sort(key=lambda x: (-x["value"], x["start"]))
        
        for program in all_candidates:
            temp_solution = candidate + [program]
            if self.is_valid_solution(temp_solution):
                candidate.append(program)
                
        return candidate
    
    def repair_random(self, partial_solution, removed):
        """Random repair by adding valid programs"""
        candidate = copy.deepcopy(partial_solution)
        remaining_programs = [p for p in self.programs if p not in candidate]
        
        # Combine removed and remaining programs
        all_candidates = removed + remaining_programs
        random.shuffle(all_candidates)
        
        for program in all_candidates:
            temp_solution = candidate + [program]
            if self.is_valid_solution(temp_solution):
                candidate.append(program)
                
        return candidate
    
    def repair_tür_balanced(self, partial_solution, removed):
        """Repair focusing on tür balance"""
        candidate = copy.deepcopy(partial_solution)
        remaining_programs = [p for p in self.programs if p not in candidate]
        
        tür_counts = {tür: 0 for tür in self.unique_türler}
        for program in candidate:
            tür_counts[program["Tür"]] += 1
        
        def tür_score(p):
            proposed_counts = tür_counts.copy()
            proposed_counts[p["Tür"]] += 1
            total = sum(proposed_counts.values())
            if total == 0:
                return 0
            max_diff = max(proposed_counts.values()) - min(proposed_counts.values())
            return -max_diff
        
        all_candidates = removed + remaining_programs
        all_candidates.sort(key=lambda x: (tür_score(x), -x["value"]), reverse=True)
        
        for program in all_candidates:
            temp_solution = candidate + [program]
            if self.is_valid_solution(temp_solution):
                candidate.append(program)
                tür_counts[program["Tür"]] += 1
                
        return candidate
    
    def run(self):
        no_improve = 0
        
        for iteration in range(self.max_iterations):
            if no_improve >= self.max_no_improve:
                break
                
            destroy_op = random.choices(
                [self.destroy_random, self.destroy_weakest, self.destroy_cluster],
                weights=self.destroy_weights,
                k=1
            )[0]
            
            repair_op = random.choices(
                [self.repair_greedy, self.repair_random, self.repair_tür_balanced],
                weights=self.repair_weights,
                k=1
            )[0]
            
            destruction_rate = random.choice(self.destroy_rates)
            
            destroyed, removed = destroy_op(self.current_solution, destruction_rate)
            candidate = repair_op(destroyed, removed)
            
            candidate_value = self.objective_function(candidate)
            
            if candidate_value > self.current_value:
                self.current_solution = candidate
                self.current_value = candidate_value
                no_improve = 0
                
                if candidate_value > self.best_value:
                    self.best_solution = copy.deepcopy(candidate)
                    self.best_value = candidate_value
            else:
                delta = self.current_value - candidate_value
                prob = math.exp(-delta / self.temperature)
                if random.random() < prob:
                    self.current_solution = candidate
                    self.current_value = candidate_value
                no_improve += 1
                
            self.temperature *= self.cooling_rate
            
        return self.best_solution, self.best_value
    
user_slots = [
    {"day": "Pazartesi", "start_time": "09:00", "end_time": "12:00"},
    {"day": "Pazartesi", "start_time": "14:00", "end_time": "18:00"},
    {"day": "Salı", "start_time": "10:00", "end_time": "13:00"},
    {"day": "Salı", "start_time": "15:00", "end_time": "17:00"},
    {"day": "Çarşamba", "start_time": "08:00", "end_time": "10:00"},
    {"day": "Perşembe", "start_time": "19:00", "end_time": "22:00"},
    {"day": "Cuma", "start_time": "12:00", "end_time": "15:00"},
    {"day": "Cumartesi", "start_time": "12:00", "end_time": "17:00"},
    {"day": "Pazar", "start_time": "09:00", "end_time": "15:00"}
]
programs_file = "haftalik_düzenli.xlsx"
greedy_solution, greedy_value = TV_Schedule_Greedy.greedy_scheduler(user_slots, programs_file)

alns = TvSchedulerALNS(user_slots, programs_file, initial_solution=(greedy_solution, greedy_value))
best_solution, best_value = alns.run()

print(f"Greedy solution value: {greedy_value}")
print(f"ALNS improved solution value: {best_value}")

visualize.visualize_schedule_interactive(
    user_slots, 
    [(p, {
        "day": p["Gün"],
        "start_time": p["Başlangıç Saati"],
        "end_time": p["Bitiş Saati"]
    }) for p in best_solution], 
    "alns_improved"
)    