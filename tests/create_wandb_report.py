import wandb
import wandb.apis.reports as wr
from pygit2 import Repository, Commit
from datetime import datetime, timedelta

report = wr.Report(
    project="llm-eval-sweep",
    title="Test Summary For Branch "+ Repository('.').head.shorthand + " at "+datetime.now().strftime("%m/%d/%Y, %H:%M"),
    description="Evaluate the peformance of the changes made to the service.",
)

python_filter = "branch == '"+Repository('.').head.shorthand+"' and commit_hash == '"+Repository('.').head.peel(Commit).id.hex+"'"

acc_llm_service_bar_plot = wr.PanelGrid(
    runsets=[wr.Runset(project="llm-eval-sweep", name="LLM Service Grouping", groupby=["llm_service"]).set_filters_with_python_expr(python_filter)],
    panels = [
        wr.BarPlot(
            title="Average Accuracy by LLM Service",
            metrics=["Accuracy"],
            groupby="llm_service",
            groupby_aggfunc="mean",
            groupby_rangefunc="stddev",
            layout={'w': 24, 'h': 16}  # change the layout!
        )
    ]
)

acc_question_type_bar_plot = wr.PanelGrid(
    runsets=[wr.Runset(project="llm-eval-sweep", name="Question Type Grouping", groupby=["question_type"]).set_filters_with_python_expr(python_filter)],
    panels = [
        wr.BarPlot(
            title="Average Accuracy by Question Type",
            metrics=["Accuracy"],
            groupby="question_type",
            groupby_aggfunc="mean",
            groupby_rangefunc="stddev",
            layout={'w': 24, 'h': 16}  # change the layout!
        )
    ]
)


acc_parallel_cords = wr.PanelGrid(
    runsets=[wr.Runset(project="llm-eval-sweep").set_filters_with_python_expr(python_filter)],
    panels = [
        wr.ParallelCoordinatesPlot(
            columns=[
                wr.PCColumn(metric="c::llm_service"),
                wr.PCColumn(metric="c::dataset"),
                wr.PCColumn(metric="c::question_type"),
                wr.PCColumn(metric="Accuracy"),
            ],
            layout={'w': 24, 'h': 16}  # change the layout!
        )
    ]
)

nrp_llm_service_bar_plot = wr.PanelGrid(
    runsets=[wr.Runset(project="llm-eval-sweep", name="LLM Service Grouping", groupby=["llm_service"]).set_filters_with_python_expr(python_filter)],
    panels = [
        wr.BarPlot(
            title="Average Not Wrong Percent by LLM Service",
            metrics=["Not Wrong Percent"],
            groupby="llm_service",
            groupby_aggfunc="mean",
            groupby_rangefunc="stddev",
            layout={'w': 24, 'h': 16}  # change the layout!
        )
    ]
)

nrp_question_type_bar_plot = wr.PanelGrid(
    runsets=[wr.Runset(project="llm-eval-sweep", name="Question Type Grouping", groupby=["question_type"]).set_filters_with_python_expr(python_filter)],
    panels = [
        wr.BarPlot(
            title="Average Not Wrong Percent by Question Type",
            metrics=["Not Wrong Percent"],
            groupby="question_type",
            groupby_aggfunc="mean",
            groupby_rangefunc="stddev",
            layout={'w': 24, 'h': 16}  # change the layout!
        )
    ]
)


nrp_parallel_cords = wr.PanelGrid(
    runsets=[wr.Runset(project="llm-eval-sweep").set_filters_with_python_expr(python_filter)],
    panels = [
        wr.ParallelCoordinatesPlot(
            columns=[
                wr.PCColumn(metric="c::llm_service"),
                wr.PCColumn(metric="c::dataset"),
                wr.PCColumn(metric="c::question_type"),
                wr.PCColumn(metric="Not Wrong Percent"),
            ],
            layout={'w': 24, 'h': 16}  # change the layout!
        )
    ]
)

table = wr.PanelGrid(
    runsets=[wr.Runset(project="llm-eval-sweep").set_filters_with_python_expr(python_filter)],
    panels = [
        wr.WeavePanelSummaryTable(table_name="qa_results",
            layout={'w': 24, 'h': 16}  # change the layout!
        )
    ]
)

report.blocks = [acc_llm_service_bar_plot, acc_question_type_bar_plot, acc_parallel_cords, table, nrp_llm_service_bar_plot, nrp_question_type_bar_plot, nrp_parallel_cords]
report.save()

print(report.url)