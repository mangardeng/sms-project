import { useEffect, useState } from "react";

import { gradeScaleApi } from "../api/examinations";
import { printHtml } from "../utils/print";
import { buildReportCardDocument, buildReportCardHtml, REPORT_CARD_CSS } from "../utils/reportCard";

/**
 * The student's end-of-term examination card: every subject with midterm + end-of-term marks added
 * together, the grade and remark, the overall total/average/grade and the position in class.
 * `card` is the response of /examinations/term-summaries/{id}/report-card/.
 */
export default function TermReportCard({ card, canPrint = true }) {
  const [scale, setScale] = useState([]);

  useEffect(() => {
    gradeScaleApi
      .list({ page_size: 50 })
      .then((data) => setScale(data.results || data))
      .catch(() => setScale([]));
  }, []);

  return (
    <div>
      <style>{REPORT_CARD_CSS}</style>
      <div dangerouslySetInnerHTML={{ __html: buildReportCardHtml(card, scale) }} />
      {canPrint && (
        <div style={{ marginTop: 12 }}>
          <button className="btn btn-primary" type="button" onClick={() => printHtml(buildReportCardDocument(card, scale))}>
            🖨 Print report card
          </button>
        </div>
      )}
    </div>
  );
}
