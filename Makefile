.PHONY: test lint seed evaluate optimize reconcile clean

PYTHONPATH := src

test:
	PYTHONPATH=$(PYTHONPATH) pytest -v

seed:
	PYTHONPATH=$(PYTHONPATH) python3 -m megamakmur.cli seed --csv data/scouting_radar_2026_10_31.csv --db data/megamakmur.db

evaluate:
	PYTHONPATH=$(PYTHONPATH) python3 -m megamakmur.cli radar --csv data/scouting_radar_2026_10_31.csv

optimize:
	PYTHONPATH=$(PYTHONPATH) python3 -m megamakmur.cli allocate --csv data/scouting_radar_2026_10_31.csv --capital 1000000000

reconcile:
	PYTHONPATH=$(PYTHONPATH) python3 -m megamakmur.cli reconcile --jobs data/workshop_jobs_2026_10.csv --mutations data/bank_qris_mutations_2026_10.csv

clean:
	rm -rf .pytest_cache build dist src/*.egg-info data/*.db
