# Metric cards

| Name | 中文名称 | ID | Level | Formula | Unit | Source |
|---|---|---|---|---|---|---|
| Aggregation Index (AI) | 聚集度指数 | aggregation_index | class, landscape | \( AI = 100 \times \frac{g_{ii}}{\max g_{ii}} \) | percent | [source](https://doi.org/10.1023/A:1008102521322) |
| Patch Area (AREA) | 斑块面积 | area | patch | \( AREA = a_{ij} \) | square_metre | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| Patch Area Coefficient of Variation (AREA_CV) | 斑块面积变异系数 | area_cv | class | \( AREA\_CV = 100 \times \frac{s_a}{\bar{a}} \) | percent | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| Mean Patch Area (AREA_MN) | 平均斑块面积 | area_mean | class | \( AREA\_MN = \bar{a} \) | square_metre | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| Patch Area Standard Deviation (AREA_SD) | 斑块面积标准差 | area_sd | class | \( AREA\_SD = s_a \) | square_metre | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| Edge Density (ED) | 边缘密度 | edge_density | class, landscape | \( ED = \frac{E}{A_{\mathrm{ha}}} \) | metre_per_hectare | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| Fractal Dimension Index (FRAC) | 分形维数指数 | fractal_dimension | patch | \( FRAC = \frac{2\ln(0.25P)}{\ln A} \) | dimensionless | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| Largest Patch Index (LPI) | 最大斑块指数 | largest_patch_index | class, landscape | \( LPI = 100 \times \frac{\max(a_{ij})}{A} \) | percent | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| Number of Patches (NP) | 斑块数量 | number_of_patches | class, landscape | \( NP = n \) | count | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| Patch Density (PD) | 斑块密度 | patch_density | class, landscape | \( PD = 100 \times \frac{NP}{A_{\mathrm{ha}}} \) | patches_per_100_hectare | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| Patch Perimeter (PERIM) | 斑块周长 | perimeter | patch | \( PERIM = P_{ij} \) | metre | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| Perimeter-Area Ratio (PARA) | 周长面积比 | perimeter_area_ratio | patch | \( PARA = \frac{P_{ij}}{a_{ij}} \) | inverse_metre | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| Proportion of Landscape (PLAND) | 景观比例 | proportion_of_landscape | class | \( PLAND = 100 \times \frac{\sum_j a_{ij}}{A} \) | percent | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| Radius of Gyration (GYRATE) | 回转半径 | radius_of_gyration | patch | \( GYRATE = \sqrt{\frac{1}{n}\sum_{r=1}^{n}\lVert\mathbf{x}_r-\bar{\mathbf{x}}\rVert^2} \) | metre | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| Patch Shape Index (SHAPE) | 斑块形状指数 | shape_index | patch | \( SHAPE = \frac{P}{2\sqrt{\pi A}} \) | dimensionless | [source](https://doi.org/10.2307/3781151) |
| Mean Patch Shape Index (SHAPE_MN) | 平均斑块形状指数 | shape_index_mean | class | \( SHAPE\_MN = \frac{1}{n}\sum_{j=1}^{n}SHAPE_{ij} \) | dimensionless | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| Shannon's Diversity Index (SHDI) | 香农多样性指数 | shannon_diversity | landscape | \( SHDI = -\sum_{i=1}^{m}q_i\ln q_i \) | dimensionless | [source](https://doi.org/10.1002/j.1538-7305.1948.tb01338.x) |
| Shannon's Evenness Index (SHEI) | 香农均匀度指数 | shannon_evenness | landscape | \( SHEI = \frac{SHDI}{\ln m} \) | dimensionless | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| Simpson's Diversity Index (SIDI) | 辛普森多样性指数 | simpson_diversity | landscape | \( SIDI = 1-\sum_{i=1}^{m}q_i^2 \) | dimensionless | [source](https://doi.org/10.1038/163688a0) |
| Total Area (TA) | 总面积 | total_area | class, landscape | \( TA = \sum_i a_i \) | square_metre | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |
| Total Edge (TE) | 总边缘长度 | total_edge | class | \( TE = E \) | metre | [source](https://www.fs.usda.gov/pnw/pubs/pnw_gtr351.pdf) |

Cards marked as original identify a cited original source. Definition references identify a transparent definition source without claiming original authorship.
