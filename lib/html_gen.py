from html import escape
import json
import locale
from db.db import QUERY_TYPE
import os
from flask import render_template_string


locale.setlocale(locale.LC_ALL, os.environ.get("LC_ALL", "en_US.UTF-8"))


def get_html_table(result: tuple, query_type: QUERY_TYPE) -> str:
    """Returns a partial HTML table with the given data."""

    assert result is not None

    html_head = """
      <div class="table-container">
        <table class="table">
        <thead>
            <tr>
            <th>CIK</th>
            <th>Company</th>
            <th>CUSIP</th>
            <th>Date</th>
            <th>Balance</th>
            <th>Value</th>
            </tr>
        </thead>
        <tbody>"""
    html_fragments = [html_head]
    original_value = None
    if len(result) > 0 and check_same_cik(result) and query_type != QUERY_TYPE.REAL:
        original_value = result[0].get("value")
    for item in result:
        value_row = get_value_row(item, original_value)
        html_fragments.append(
            f"""
        <tr>
            <td>{escape(item['cik'])}</td>
            <td>{escape(item['company'])}</td>
            <td>{escape(item['cusip'])}</td>
            <td>{escape(item['date'])}</td>
            <td>{escape(str(item['balance']))}</td>
            {value_row}
        </tr>
        """
        )
    html_footer = "</tbody></table></div>"
    html_fragments.append(html_footer)
    return "".join(html_fragments)


def check_same_cik(dict_list: tuple):
    if not dict_list:
        return False

    first_cik = dict_list[0].get("cik")

    if first_cik is None:
        return False

    for item in dict_list:
        if "cik" not in item:
            return False
        if item["cik"] != first_cik:
            return False

    return True


def get_value_row(item: dict, original_value: float) -> str:
    value = item.get("value")
    if value is None:
        return "<td>No value found</td>"
    elif original_value is None:
        return f"""<td><p>{escape(locale.currency(float(value), grouping=True))}</p></td>"""
    elif value < original_value:
        return f"""<td><p style="color: red;">{escape(locale.currency(float(value), grouping=True))}</p></td>"""
    elif value > original_value:
        return f"""<td><p style="color: green;">{escape(locale.currency(float(value), grouping=True))}</p></td>"""
    else:
        return f"""<td><p>{escape(locale.currency(float(value), grouping=True))}</p></td>"""


def get_html_visualization(result: tuple, query_type: QUERY_TYPE) -> str:
    """Returns one or more partial HTML visualizations with the given data."""

    assert result is not None
    assert query_type in QUERY_TYPE

    visualization_title = """<div class="visualization-container">"""
    visualization_body = ""
    if query_type == QUERY_TYPE.LATEST:
        visualization_body = get_visual_body(result, query_type, "Latest Company Filings")
    elif query_type == QUERY_TYPE.REAL:
        visualization_body = get_visual_body(result[:20], query_type, "")
    else:
        for cik in set([item["cik"] for item in result]):
            company_data = [item for item in result if item["cik"] == cik]
            company = company_data[0]["company"]
            visualization_body += get_visual_body(company_data, query_type, company)

    visualization_footer = "</div>"
    return visualization_title + visualization_body + visualization_footer


def get_visual_body(result: tuple, query_type: QUERY_TYPE, title) -> str:
    """Returns a partial HTML visualization body with the given data"""

    assert result is not None
    assert query_type in QUERY_TYPE

    # Nothing to visualize, we'll leave this section empty
    if len(result) <= 1:
        return ""

    return f"""
    <div id="chart"></div>
        <script>
            document.body.dispatchEvent(new CustomEvent('dataUpdated', {{
                detail: {{ 
                    data: {json.dumps(result)},
                    queryType: {json.dumps(str(query_type.name.lower()))},
                    title: {json.dumps(title)}
                }}
            }}));
        </script>
    """


def error_dialog(msg: str) -> str:
    """Returns a partial HTML error dialog with the given message"""
    return f"""
        <table class="table">
        <thead>
            <tr>
            <th>CIK</th>
            <th>Company</th>
            <th>CUSIP</th>
            <th>Date</th>
            <th>Balance</th>
            <th>Value</th>
            </tr>
        </thead>
    <div class="alert alert-danger alert-dismissible fade show" role="alert">
        <strong>Error!</strong> {escape(msg)}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
    </table>
    """

def get_pagination_html(current_page, total_pages, query_type):
    if query_type == QUERY_TYPE.LATEST:
        endpoint = "/search-latest" 
    elif query_type == QUERY_TYPE.REAL:
        endpoint = "/search-real" 
    else:
        endpoint = "/search-historical"
    return render_template_string("""
    <div class="pagination">
        {% if current_page > 1 %}
            <button hx-post="{{ endpoint }}"
                    hx-target="#search-results"
                    hx-include="#search-input"
                    hx-vals='{"page": {{ current_page - 1 }} }'
                    class="page-btn">
                Previous
            </button>
        {% endif %}
        {% for page_num in range(1, total_pages + 1) %}
            <button hx-post="{{ endpoint }}"
                    hx-target="#search-results"
                    hx-include="#search-input"
                    hx-vals='{"page": {{ page_num }} }'
                    class="page-btn {% if page_num == current_page %}active{% endif %}">
                {{ page_num }}
            </button>
        {% endfor %}
        {% if current_page < total_pages %}
            <button hx-post="{{ endpoint }}"
                    hx-target="#search-results"
                    hx-include="#search-input"
                    hx-vals='{"page": {{ current_page + 1 }} }'
                    class="page-btn">
                Next
            </button>
        {% endif %}
    </div>
    """, current_page=current_page, total_pages=total_pages, endpoint=endpoint)