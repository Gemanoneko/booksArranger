"""Books Arranger normal windowless open entrypoint."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from app_launcher import main
raise SystemExit(main(restart=False))
