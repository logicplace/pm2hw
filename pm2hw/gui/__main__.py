# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys

def main():
	from . import root, game_list
	from ..config import config_file, save as save_config

	root.mainloop()
	print("Saving config to", config_file)
	save_config()
	game_list.cleanup()
	return 0


if __name__ == "__main__":
	sys.exit(main())
