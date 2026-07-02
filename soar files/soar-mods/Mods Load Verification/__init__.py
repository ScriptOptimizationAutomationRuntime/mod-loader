# Do not delete this script. It helps you know if your mods are loading correctly. 

import sys

def initialize_addon():
    failed_mods = []
    
    for mod_name, module in list(sys.modules.items()):
        if mod_name not in ["soar_main", "soar_autocode", "soar_avss", "Mods Load Verification"] and hasattr(module, "__file__"):
            if "soar-mods" in getattr(module, "__file__", ""):
                if hasattr(module, "load_error_flag") or getattr(module, "__spec__", None) is None:
                    failed_mods.append(mod_name)

    if failed_mods:
        print(f"[!] Mods Load Verification: Detected issues in {len(failed_mods)} mod(s): {', '.join(failed_mods)}")
    else:
        print("Mods loaded successfully.")
