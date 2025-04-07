import random
import numpy as np
import pandas as pd
from datetime import datetime
from collections import defaultdict
import visualize

def time_to_minutes(t):
    return datetime.strptime(t, "%H:%M").hour * 60 + datetime.strptime(t, "%H:%M").minute

class TvSchedulerGA:
    def __init__(self, user_slots, program_file, population_size=100, generations=100, mutation_rate=0.1, tournament_size=10, tur_dagilimi=False):
        self.user_slots = user_slots
        self.programs = pd.read_excel(program_file).to_dict(orient='records')
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.tournament_size = tournament_size
        self.final_schedule = []
        self.tur_dagilimi = tur_dagilimi

    def filter_programs(self, slot):
        """Belirtilen zaman dilimi için uygun programları seçer"""
        slot_start = time_to_minutes(slot["start_time"])
        slot_end = time_to_minutes(slot["end_time"])
        slot_day = slot["day"]
        
        selected_programs = []
        for program in self.programs:
            if program["Gün"] != slot_day:
                continue
            start = time_to_minutes(program["Başlangıç Saati"])
            end = time_to_minutes(program["Bitiş Saati"])
            if slot_start <= start and end <= slot_end:
                selected_programs.append(program)
        print(f"Filtrelenen program sayısı ({slot_day} {slot_start}-{slot_end}): {len(selected_programs)}")
        return selected_programs

    def fitness(self, individual, slot):
        if not individual:
            return -float('inf')
        total_value = 0
        used_time = []
        penalties = 0
        type_counts = defaultdict(int)
        consecutive_types = []
        
        # Slot zamanlarını dakikaya çevir
        slot_start = time_to_minutes(slot["start_time"])
        slot_end = time_to_minutes(slot["end_time"])
        slot_duration = slot_end - slot_start
        
        # Programları başlangıç saatine göre sırala
        sorted_individual = sorted(individual, key=lambda x: time_to_minutes(x["Başlangıç Saati"]))
        max_in_individual = max(prog["value"] for prog in individual) if individual else 1
        base_penalty = max_in_individual + 100  # Cezaların temel birimi
        previous_end = None  # Önceki programın bitiş saatini tutmak için
        
        # Slot başlangıcı ile ilk program arası 15 dakikadan az olmalı
        if sorted_individual:
            first_program_start = time_to_minutes(sorted_individual[0]["Başlangıç Saati"])
            initial_gap = first_program_start - slot_start
            if initial_gap > 15:
                penalties += base_penalty
        
        previous_end = None
        total_scheduled_time = 0
        for program in sorted_individual:
            start = time_to_minutes(program["Başlangıç Saati"])
            end = time_to_minutes(program["Bitiş Saati"])
            program_type = program["Tür"]
    
            # Çakışma kontrolü (10 dakikadan fazla)
            overlap = any(
                (start < prev_end + 10 and end > prev_start - 10)
                for prev_start, prev_end in used_time
            )
            if overlap:
                penalties += base_penalty
    
            # Ardışık tür kontrolü (3 aynı tür yasak)
            consecutive_types.append(program_type)
            if len(consecutive_types) >= 3:
                if consecutive_types[-3] == consecutive_types[-2] == consecutive_types[-1]:
                    penalties += base_penalty
                else:
                    consecutive_types = consecutive_types[-2:]
    
            # Maksimum 15 dakika boşluk kontrolü
            if previous_end is not None and (start - previous_end) > 15:
                penalties += base_penalty
    
            previous_end = end
            used_time.append((start, end))
            total_value += program["value"]
            type_counts[program_type] += 1
    
        if self.tur_dagilimi == True:
            # Tür dengesizliği cezası
            type_balance_penalty = sum(
                abs(type_counts[t1] - type_counts[t2]) 
                for t1 in type_counts for t2 in type_counts
            ) / 2
        else: type_balance_penalty=0
        
        if sorted_individual:
            last_program_end = time_to_minutes(sorted_individual[-1]["Bitiş Saati"])
            final_gap = slot_end - last_program_end
            if final_gap > 15:
                penalties += base_penalty
       
        #base_penalty * 0.01 * (final_gap - 15)
        
        # total_idle_time = slot_duration - total_scheduled_time
        # if total_idle_time > (0.1 * slot_duration):
        #     excess_idle = total_idle_time - (0.1 * slot_duration)
        #     penalties += base_penalty * 0.1 * excess_idle
            
        return total_value - (penalties + type_balance_penalty)

    # def create_individual(self, available_programs):
    #     return random.sample(available_programs, random.randint(5, min(20, len(available_programs))))
    def create_individual(self, available_programs, slot):
        slot_start = time_to_minutes(slot["start_time"])
        slot_end = time_to_minutes(slot["end_time"])
        slot_duration = slot_end - slot_start
        
        individual = []
        current_time = slot_start
        remaining_programs = available_programs.copy()
        
        min_fill_duration = 0.7 * slot_duration
        filled_duration = 0
        
        while (current_time < slot_end and 
               filled_duration < min_fill_duration and 
               remaining_programs):
            
            possible_programs = [
                p for p in remaining_programs 
                if (time_to_minutes(p["Başlangıç Saati"]) >= current_time and
                    time_to_minutes(p["Bitiş Saati"]) <= slot_end)
            ]
            
            if not possible_programs:
                break
                
            programs_with_weights = [
                (p, p["value"]/(time_to_minutes(p["Bitiş Saati"])-time_to_minutes(p["Başlangıç Saati"])))
                for p in possible_programs
            ]
            total_weight = sum(w for _, w in programs_with_weights)
            
            if total_weight <= 0:
                selected = random.choice(possible_programs)
            else:
                selected = random.choices(
                    [p for p, _ in programs_with_weights],
                    weights=[w for _, w in programs_with_weights],
                    k=1
                )[0]
            
            individual.append(selected)
            program_duration = (time_to_minutes(selected["Bitiş Saati"]) - 
                              time_to_minutes(selected["Başlangıç Saati"]))
            filled_duration += program_duration
            current_time = time_to_minutes(selected["Bitiş Saati"])
            
            current_time += random.randint(0, 15)

            remaining_programs.remove(selected)
        
        return individual

    def crossover(self, parent1, parent2):
        split1 = len(parent1) // 3
        split2 = len(parent2) // 3
        child = parent1[:split1] + parent2[split2:]
        return child

    def mutate(self, individual, available_programs):
        if random.random() < self.mutation_rate:
            if random.random() < 0.5 and individual:
                individual.pop(random.randint(0, len(individual) - 1))
            else:
                individual.append(random.choice(available_programs))
        return individual

    def tournament_selection(self, population,slot):
        tournament = random.sample(population, self.tournament_size)
        tournament = sorted(tournament, key=lambda ind: self.fitness(ind, slot), reverse=True)
        return tournament[0]

    def evolve(self, available_programs,slot):
        population = [self.create_individual(available_programs,slot) for _ in range(self.population_size)]

        for i in range(self.generations):
            new_population = []
            while len(new_population) < self.population_size:
                parent1 = self.tournament_selection(population,slot)
                parent2 = self.tournament_selection(population,slot)
                child = self.crossover(parent1, parent2)
                child = self.mutate(child, available_programs)
                new_population.append(child)

            population = new_population
            print(f"{i+1}. generation fitness: {self.fitness(population[0], slot)}")

        return max(population, key=lambda ind: self.fitness(ind, slot))

    def schedule(self):
        total_weekly_score = 0  # Haftalık toplam puan
        for slot in self.user_slots:
            print(f"Slot: {slot['day']} {slot['start_time']} - {slot['end_time']} için planlanıyor...")
            available_programs = self.filter_programs(slot)
    
            if not available_programs:
                print(f"Uygun program bulunamadı: {slot['day']} {slot['start_time']} - {slot['end_time']}")
                continue
    
            best_schedule_for_slot = self.evolve(available_programs,slot)
            
            # Slot için toplam puan
            slot_score = sum(program["value"] for program in best_schedule_for_slot)
            total_weekly_score += slot_score
    
            print(f"{slot['day']} {slot['start_time']} - {slot['end_time']} slotu için toplam puan: {slot_score}")
    
            # Final programa ekleme
            self.final_schedule.extend([(program, slot) for program in best_schedule_for_slot])
    
        print(f"\nHaftalık toplam puan: {total_weekly_score}")
        #visualize.visualize_schedule_interactive(self.user_slots, self.final_schedule, "ga")
        return self.final_schedule

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
def main(user_slots):

    ga_scheduler = TvSchedulerGA(user_slots, "haftalik_düzenli.xlsx")
    ga_solution = ga_scheduler.schedule()
    print("Final Program:")
    for program, slot in ga_solution:
        print(f"{slot['day']} {slot['start_time']}-{slot['end_time']} -> {program['Başlangıç Saati']}-{program['Bitiş Saati']} {program['Tür']}")

if __name__ == "__main__":
    main(user_slots)
