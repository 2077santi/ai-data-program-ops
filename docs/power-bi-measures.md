# Power BI measures

The CSVs in `data/` load as-is. Relationships (single direction, many-to-one):

- `fact_production[batch_id]` → `dim_batch[batch_id]`
- `fact_production[annotator_id]` → `dim_annotator[annotator_id]`
- `fact_timesheet[annotator_id]` → `dim_annotator[annotator_id]`
- `dim_batch[workstream_id]` → `dim_workstream[workstream_id]`
- `dim_annotator[workstream_id]` → `dim_workstream[workstream_id]`
- a `Calendar` date table marked as date table, related to `fact_production[date]` and `fact_timesheet[date]`

```DAX
Units = SUM ( fact_production[units] )

Handle Hours = SUM ( fact_production[handle_hours] )

UPH = DIVIDE ( [Units], [Handle Hours] )

UPH vs Plan % = DIVIDE ( [UPH], AVERAGE ( dim_workstream[target_uph] ) )

Quality = DIVIDE ( SUM ( fact_production[qa_passed] ), SUM ( fact_production[qa_sampled] ) )

Quality Gap pp = ( [Quality] - AVERAGE ( dim_workstream[quality_target] ) ) * 100

Paid Hours = SUM ( fact_timesheet[logged_hours] )

Utilization = DIVIDE ( [Handle Hours], [Paid Hours] )

Labor Cost =
SUMX (
    fact_timesheet,
    fact_timesheet[logged_hours] * RELATED ( dim_annotator[hourly_cost_eur] )
)

Revenue =
SUMX (
    fact_production,
    fact_production[units] * RELATED ( dim_workstream[price_per_unit] )
)

Gross Margin % = DIVIDE ( [Revenue] - [Labor Cost], [Revenue] )

Cost per Unit = DIVIDE ( [Labor Cost], [Units] )

Batches Delivered On Time % =
VAR Delivered =
    FILTER (
        dim_batch,
        CALCULATE ( SUM ( fact_production[units] ) ) >= dim_batch[units] - 0.5
    )
VAR OnTime =
    FILTER (
        Delivered,
        CALCULATE ( MAX ( fact_production[date] ) ) <= dim_batch[due_date]
    )
RETURN DIVIDE ( COUNTROWS ( OnTime ), COUNTROWS ( Delivered ) )

Quality RAG =
VAR Gap = [Quality] - AVERAGE ( dim_workstream[quality_target] )
RETURN SWITCH ( TRUE (), Gap < -0.02, "Red", Gap < 0, "Amber", "Green" )

Margin RAG = SWITCH ( TRUE (), [Gross Margin %] < 0, "Red", [Gross Margin %] < 0.15, "Amber", "Green" )
```

The delivery forecast stays in Python (`ops/pipeline.py`). It is a day-by-day simulation, which DAX is not built for. Export `reports/program_results.json` → `forecast` to a table if you want it in the report.
