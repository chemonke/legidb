## Motivation
I have this delusion that makes me think laws should be easy to follow. Unfortunately, legislators and authors of legal documents appear to disagree. Laws are written in the most incomprehensible fashion imaginable, information is scattered across a thousand pages and fifteen different documents and, of course, there is no database that one could query to find out which laws one may potentially be violating.

## Important Definitions
- (Food) simulant: A compound or mixture intended to mimic the behavior of food in order facilitate migration of compounds from packaging into food.
- Specific migration: An experimental setup where a product is put into contact with a food simulant for a defined period at a defined temperature. The media produced by this experiment are then analyzed for specific compounds.
- Specific migration limit (SML): The maximum amount of a compound that is legally peritted to migrate from packaging into food.

## About the project
I chose the EU regulation 10/2011 `Commission Regulation (EU) No 10/2011 of 14 January 2011 on plastic materials and articles intended to come into contact with food Text with EEA relevance` to create a proof of concept, simply because I am somewhat familiar with the regulation. There is nothing inherently special about the EU in this regard, other regulatory bodies are just as bad, if not worse.

The regulation outlines rules governing food contact materials (e.g. packaging, cooking utensils, food production components etc.). It also provides specific testing requirements. So, if we model these requirements and limits in a database, we can use queries to tell users which tests they must perform, and which rules/limits apply.

We need to create a suitable schema for the following:

- Annex I: Table 1: Authorized Substances
- Annex I: Table 2: Group restrictions of substances
- Annex III Table 1: List of food simulants
- Annex III Table 2: List of food simulant assignments
- Annex V: Table 1: Selection of test time
- Annex V: Table 2: Selection of test temperature


### Schema
![generated with `schemacrawler` and `graphviz`](./docs/schema.png)


```
nix shell nixpkgs#schemacrawler nixpkgs#graphviz --command \
  schemacrawler \
    --server=mysql \
    --host=127.0.0.1 --port=3307 \
    --database=legidb --user=legidb --password=legidb \
    --info-level=standard \
    --command=schema \
    --output-format=png \
    --output-file=docs/schema.png
```
## Schema Design Considerations
Annex I drives everything, so `substances` and `sm_entries` hold the CAS/FCM/EC references plus SML/FRF flags. Group restrictions live in `group_restrictions` with the join table `sm_entry_group_restrictions` to mirror Annex I Table 2. Foods and simulants mirror Annex III: `food_categories` lists categories with FRF hints, `simulants` names them, and `food_category_simulants` expresses the many-to-many assignment. Annex V time/temperature selections are flat reference tables (`sm_time_conditions`, `sm_temp_conditions`) because the regulation expresses them as independent lookups rather than relationships.

Strictly speaking it would not be necessary to have the table `substances` and `sm_entries` be separate entities in this case, but I opted to do it this way in case I decide to add additional regulations at a later point.

## Installation
### Nix (native)
To simply test the page you can initialize the db using `nix run github:chemonke/legidb#db-start`

and start the flask app with `nix run github:chemonke/legidb#app`.

If you have cloned the repo you can do the same with `nix run .#db-start` and `nix run .#app`

If you want to work on the code, clone the repo and run `nix develop` to enter the devshell.

To stop and remove the db use `nix run .#db-stop -- --clean`. If you wish to preserve modifications you made, omit the `-- -- clean` flag.

### Docker
If you don’t want to install Nix (why not?!), use the dev container that bundles the same tooling as `nix develop`.

- Pull the image (replace the tag if you publish elsewhere):  
  `docker pull ghcr.io/chemonke/legidb-dev:latest`
- Run it with your working tree mounted:  
  `docker run -it --rm -v "$PWD":/workspace -p 5000:5000 -p 3307:3307 ghcr.io/chemonke/legidb-dev:latest`
- Inside the container:  
  `scripts/start_ephemeral_mariadb.sh` (starts MariaDB on 3307 and loads schema/sample data)  
  `python run.py` (or `nix run .#app` if you prefer)

To build the image yourself for pushing to a registry:  
`nix build .#docker-image-dev`


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
