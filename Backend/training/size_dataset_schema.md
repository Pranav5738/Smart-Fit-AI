# Size Dataset Schema (Real Data)

Use this schema for training a real size model (no synthetic rows):

## Required Columns
- `chest_cm` (float)
- `waist_cm` (float)
- `shoulder_cm` (float)
- `age_group` (`child|teen|adult`)
- `gender` (`male|female|unisex`)
- `fit_preference` (`slim|regular|relaxed`)
- `size_label` (target class, e.g. `XS,S,M,L,XL,XXL,10Y,12Y,...`)

## Optional Columns
- `brand` (string)
- `category` (`tees|jeans|jackets|...`)
- `source` (device/store/region)
- `height_cm` (float)

## Example Row
```csv
chest_cm,waist_cm,shoulder_cm,age_group,gender,fit_preference,size_label,brand,category
98.4,84.9,44.2,adult,male,regular,M,Nike,tees
```

## Quality Rules
- Use measured body dimensions in cm.
- Remove rows with missing target size.
- Keep class balance reasonably even across sizes.
- Split train/validation by person (avoid leakage from same person in both sets).
