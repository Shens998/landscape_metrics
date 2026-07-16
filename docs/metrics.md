# Metric cards

| ID | Level | Formula | Unit | Source |
|---|---|---|---|---|
| aggregation_index | class, landscape | 100 * g_ii / max_g_ii; landscape level uses sums over classes | percent | [source](https://doi.org/10.1023/A:1008102521322) |
| area | patch | cell_count * pixel_width * pixel_height | square_metre | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| area_cv | class | 100 * sample_sd(patch_area) / mean(patch_area) | percent | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| area_mean | class | mean(patch_area) | square_metre | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| area_sd | class | sample standard deviation of patch_area | square_metre | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| edge_density | class, landscape | total_edge_metre / valid_landscape_area_hectare | metre_per_hectare | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| fractal_dimension | patch | 2 * ln(0.25 * perimeter) / ln(area) | dimensionless | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| largest_patch_index | class, landscape | 100 * max(patch_area) / valid_landscape_area | percent | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| number_of_patches | class, landscape | count of labeled patches | count | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| patch_density | class, landscape | number_of_patches / valid_landscape_area_hectare * 100 | patches_per_100_hectare | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| perimeter | patch | sum of valid class interfaces and selected landscape exterior sides | metre | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| perimeter_area_ratio | patch | perimeter / area | inverse_metre | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| proportion_of_landscape | class | 100 * class_area / valid_landscape_area | percent | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| radius_of_gyration | patch | sqrt(mean squared distance from cell centers to their centroid) | metre | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| shape_index | patch | perimeter / (2 * sqrt(pi * area)) | dimensionless | [source](https://doi.org/10.2307/3781151) |
| shape_index_mean | class | mean(patch_shape_index) | dimensionless | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| shannon_diversity | landscape | -sum(q_i * ln(q_i)) for positive class proportions | dimensionless | [source](https://doi.org/10.1002/j.1538-7305.1948.tb01338.x) |
| shannon_evenness | landscape | shannon_diversity / ln(class_count) | dimensionless | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| simpson_diversity | landscape | 1 - sum(q_i squared) | dimensionless | [source](https://doi.org/10.1038/163688a0) |
| total_area | class, landscape | sum of valid cell areas | square_metre | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| total_edge | class | sum of class edge lengths | metre | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |

Cards marked as original identify a cited original source. Definition references identify a transparent definition source without claiming original authorship.
