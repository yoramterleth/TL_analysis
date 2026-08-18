
#%%
img_size = 4   # in mb, average size of the odin test images during daylight
total_storage = 128    # gb on card
every_n_minutes = 60/60
hours_of_the_day_running = 24

image_rate = 60 / every_n_minutes  # images per hour


image_per_day = image_rate* hours_of_the_day_running

total_storage_mb = total_storage *1000
max_images = total_storage_mb / img_size
days_of_storage = max_images / image_per_day

print("Storage capacity: " + str(days_of_storage) + ' days')

print('Equivelant to : '+ str(days_of_storage*image_per_day)+' images taken.')
# %%
# --- Battery Life Calculator ---
# Update these parameters

battery_capacity_ah = 63        # battery capacity in Ah
battery_voltage      = 12       # battery voltage in V
efficiency           = 0.85     # real-world efficiency factor (0-1)

# --- Provide EITHER a current draw OR a power draw (leave the other as None) ---
load_current_a       = None     # device current draw in A
load_power_w         = 1     # device power draw in W

# --- Calculation ---
battery_capacity_wh = battery_capacity_ah * battery_voltage
usable_capacity_wh  = battery_capacity_wh * efficiency

if load_power_w is not None:
    power_draw_w = load_power_w
elif load_current_a is not None:
    power_draw_w = load_current_a * battery_voltage
else:
    raise ValueError("Provide either load_current_a or load_power_w")

battery_life_hours = usable_capacity_wh / power_draw_w
battery_life_days  = battery_life_hours / 24

# --- Results ---
print(f"Battery capacity:       {battery_capacity_wh:.2f} Wh")
print(f"Usable capacity:        {usable_capacity_wh:.2f} Wh (after efficiency losses)")
print(f"Load power draw:        {power_draw_w:.3f} W")
print(f"Estimated battery life: {battery_life_hours:.2f} hours ({battery_life_days:.2f} days)")