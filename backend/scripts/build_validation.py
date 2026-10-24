"""Build data/validation.json from committed CIMIS data (role B).

For each station and season: totals from CIMIS (truth), raw gridded, and corrected gridded,
where station X is corrected only from the other stations' bias tables (leave-one-station-out).
Also scores Open-Meteo models best_match, era5_land and ecmwf_ifs.
Output matches schemas.ValidationResponse.
"""


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
