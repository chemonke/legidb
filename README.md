Contents:
- [About](#about)
- [Motivation](#motivation)
- [Installation](#installation)
- [Usage](#usage)
- [Planner API SQL](#planner-api-sql)

## About
This project keeps a local database of food-contact materials (FCM), simulants, and specific migration limits, and exposes a small Flask UI/API to generate test plans. The `plan` page combines foods, substances, and time/temperature conditions into a JSON plan and a rendered report.

## Motivation
I have this delusion that makes me think following laws should be comprehensible and easy to follow (weird, I know). Unfortunately legislators and authors of legal documents appear to disagree.

## Installation
### Nix (native)
To simply test ephemerally the page you can initialize the db using 

`nix run github:chemonke/legidb#db-start`

and start the flask app using 

`nix run github:chemonke/legidb#app`

if you have cloned the repo you can do the same with

`nix run .#db-start` and `nix run .#app`

If you wish to work on the code, clone the repo and run `nix develop` to enter the devshell.

To stop the db use `nix run .#db-stop`, optionally with the `-- --clean` flag to purge its contents.


### No Nix? Use the dev container
We publish (or you can build) a dev image that contains the same toolchain as `nix develop`. It lets non-Nix users work against the repo via Docker.

- Pull the image (replace `ghcr.io/chemonke/legidb-dev:latest` with your registry/tag):  
  `docker pull ghcr.io/you/legidb-dev:latest`
- Run it with your working tree mounted:  
  `docker run -it --rm -v "$PWD":/workspace -p 5000:5000 -p 3307:3307 ghcr.io/you/legidb-dev:latest`
- Inside the container:  
  `scripts/start_ephemeral_mariadb.sh` (starts MariaDB on 3307)  
  `python run.py`

To build the image yourself (for pushing to a registry), run `nix build .#docker-image-dev` and then `docker load < result`.

## Usage


## Planner API SQL
The planner API is built from a few simple SQL pulls. Below is a single-query version of the substance block that powers the plan generation. It fetches substances, their specific migration (SM) entries, and any linked group limits in one go.

```sql
-- Substitute :sub_ids with the IDs you want (e.g. :sub_id_0 = 1, :sub_id_1 = 2 …).
WITH picked_substances AS (
  SELECT s.id,
         s.cas_no,
         s.fcm_no,
         s.ec_ref_no,
         se.id AS sm_entry_id,
         se.use_as_additive_or_ppa,
         se.use_as_monomer_or_starting_substance,
         se.frf_applicable,
         se.sml,
         se.restrictions_and_specifications
  FROM substances s
  LEFT JOIN sm_entries se ON se.substance_id = s.id
  WHERE s.id IN (:sub_id_0, :sub_id_1, :sub_id_2) -- supply only as many placeholders as needed
),
group_limits AS (
  SELECT sgr.sm_id,
         gr.id AS group_restriction_id,
         gr.group_sml,
         gr.unit,
         gr.specification
  FROM group_restrictions gr
  JOIN sm_entry_group_restrictions sgr ON sgr.group_restriction_id = gr.id
)
SELECT ps.*,
       gl.group_restriction_id,
       gl.group_sml,
       gl.unit,
       gl.specification
FROM picked_substances ps
LEFT JOIN group_limits gl ON gl.sm_id = ps.sm_entry_id
ORDER BY ps.cas_no;
```

How it maps to the planner UI:
- The `picked_substances` CTE is what the planner uses to render CAS, FCM, EC, SML, FRF flags, and any restriction text.
- The `group_limits` join provides the “Group SML” badges shown under each compound.
- Similar helper queries fetch foods plus their simulants (`foods` → `food_categories` → `food_category_simulants` → `simulants`) and the time/temperature tables (`sm_time_conditions`, `sm_temp_conditions`), which are then combined into the final JSON response by the `/api/generate-plan` endpoint.
