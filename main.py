import sys

if len(sys.argv) == 1:
    from pm2hw.gui.__main__ import main
else:
    from pm2hw.__main__ import main

sys.exit(main())
