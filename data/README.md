# First Census request: Boston population

This example requests **Boston city, Massachusetts**, not individual Census tracts. It introduces the API response format before the map pipeline is built.

## Run

From the repository root, copy `.env.example` to `.env` and set your activated Census API key there. The key is not needed to launch the existing web application.

```bash
uv sync --locked
uv run --locked --env-file .env python -m boston_map.census
```

Request an API key through the [Census signup page](https://api.census.gov/data/key_signup.html). On September 17, 2026, the unauthenticated example request returned a `Missing Key` HTML page with HTTP 200. A successful HTTP status alone is therefore insufficient: the loader checks content type and validates the response structure.

The command makes one data request, with a 30-second timeout and no automatic retries or redirects. Successful, validated responses are saved under `data/raw/census/`, which is excluded from Git. Rerunning the command refreshes that local snapshot. The metadata file records the endpoint, parameters without the key, retrieval time, period, and response SHA-256 hash.

To inspect an already downloaded response without network access or a key:

```bash
uv run --locked python -m boston_map.census --from-cache
```

## Request parameters

Endpoint: `https://api.census.gov/data/2024/acs/acs5`

| Parameter | Value | Meaning |
| --- | --- | --- |
| `get` | `NAME,B01003_001E,B01003_001M` | Name, total population estimate, margin of error |
| `for` | `place:07000` | Boston city place code |
| `in` | `state:25` | Massachusetts state code |
| `key` | Local environment value | Authentication; never recorded in saved metadata |

The `2024` ACS five-year release covers **2020–2024**. It is not a current population count or a single-year estimate.

## Understanding the response

Census returns an array of arrays: the first row contains column names, and subsequent rows contain values. Numeric counts are returned as strings. This example expects exactly one data row.

| Column | Interpretation |
| --- | --- |
| `NAME` | Geographic name |
| `B01003_001E` | Estimated total population, in people |
| `B01003_001M` | Published population margin of error, in people, when numeric |
| `state` | String code `25` |
| `place` | String code `07000`; keep the leading zero |

The place GEOID is `2507000`, formed by joining the state and place strings. It is **not a tract GEOID**.

Published ACS margins of error use a 90% confidence level. When a numeric margin is available, the usual interval is estimate ± margin. Some API values are special negative codes, not measurements: for example, `-555555555` means a margin is not appropriate because the estimate is controlled to an independent population or housing estimate. The parser maps negative codes and nulls to `null` in numeric fields and preserves the raw values for interpretation; it never treats them as zero uncertainty.

This response contains no boundaries or land area. It cannot yet provide population density. The next geography step will introduce Census tracts and compatible boundary files.

Sources: [ACS five-year data](https://www.census.gov/data/developers/data-sets/acs-5year.html), [ACS value annotations](https://www.census.gov/data/developers/data-sets/acs-1year/notes-on-acs-estimate-and-annotation-values.html), [margin of error definitions](https://www.census.gov/programs-surveys/acs/methodology/sample-size-and-data-quality/sample-size-definitions.html).

## Race and origin data

```bash
uv run --locked --env-file .env python -m boston_map.census --demographics
uv run --locked python -m boston_map.census --demographics --from-cache
```

The expanded request collects estimates (`E`) and count margins of error (`M`) from [B02001: Race](https://api.census.gov/data/2024/acs/acs5/groups/B02001.html) and [B03002: Hispanic or Latino Origin by Race](https://api.census.gov/data/2024/acs/acs5/groups/B03002.html), alongside B01003. It saves a separate `boston_demographics_2024.json` and metadata file under `data/raw/census/`.

B02001 uses seven mutually exclusive groups: codes 002–008. B03002 uses seven non-Hispanic race groups (003–009) plus Hispanic/Latino of any race (012). Each partition is checked against its table total and the overall population. These are two alternative views of the same population; never sum across tables. Detailed subcategories of Two or more races are not added again.

The requested binary comparison uses **White alone (B02001_002E), regardless of Hispanic/Latino origin**, and **everyone else = total − White alone**. People reporting multiple races, including White, belong to everyone else in this definition. Non-Hispanic White alone (B03002_003E) is a different measure, retained separately.

Percentages are derived as category estimate / table total × 100 and rounded to two decimal places. Nulls and zero denominators have no percentage. Stored MOEs apply to counts, not percentages. No MOE is currently calculated for the derived everyone-else count; it is explicitly null, not zero. Raw negative special codes remain available.

### Observed city-level result

Downloaded September 18, 2026; ACS period 2020–2024, Boston city, Massachusetts (GEOID 2507000):

| Measure | Estimate | Share | Published count MOE |
| --- | ---: | ---: | ---: |
| Total population | 666,442 | 100% | ±55 |
| White alone | 308,273 | 46.26% | ±2,601 |
| Everyone else (derived) | 358,169 | 53.74% | Not calculated |
| Non-Hispanic White alone (alternative definition) | 293,690 | 44.07% | ±2,152 |

The alternative-definition row overlaps the White-alone row and must not be added to it. The two full demographic partitions each sum to 666,442. These are five-year estimates, not current counts. Tract-level acquisition and map display remain future steps.
