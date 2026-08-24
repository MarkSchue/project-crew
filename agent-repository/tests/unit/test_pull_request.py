"""Pull-request body generation tests (plan milestone M4.3 Definition of
done)."""

from tools.git_tools.pull_request import build_pull_request_body


def test_pr_body_links_run_summary_test_results_and_approval():
    body = build_pull_request_body(
        title="Deliver auth spec",
        spoc_id="SPOC-2026-0042",
        run_id="run_42",
        run_summary_ref="logs/runs/run_42/summary.md",
        test_result_refs=["public/test_results/TC-AUTH-001.md", "public/test_results/TC-AUTH-002.md"],
        approval_ref="logs/approvals/ap-1.md",
    )
    assert "logs/runs/run_42/summary.md" in body
    assert "public/test_results/TC-AUTH-001.md" in body
    assert "public/test_results/TC-AUTH-002.md" in body
    assert "logs/approvals/ap-1.md" in body


def test_pr_body_without_approval_omits_approval_link():
    body = build_pull_request_body(
        title="Deliver auth spec",
        spoc_id="SPOC-2026-0042",
        run_id="run_42",
        run_summary_ref="logs/runs/run_42/summary.md",
        test_result_refs=[],
        approval_ref=None,
    )
    # No approval link is emitted when there is no approval record.
    assert "logs/approvals" not in body
    assert "logs/runs/run_42/summary.md" in body
