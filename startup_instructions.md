python -m venv .venv
source .venv/bin/activate  # or the Windows variant above
pip install -r requirements.txt

alembic upgrade head

