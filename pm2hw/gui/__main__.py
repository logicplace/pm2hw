from . import root, game_list
from ..config import config_file, save as save_config

root.mainloop()
print("Saving config to", config_file)
save_config()
game_list.cleanup()
