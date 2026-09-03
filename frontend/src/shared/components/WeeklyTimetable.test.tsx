import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";
import WeeklyTimetable from "./WeeklyTimetable";

describe("WeeklyTimetable", () => {
  it("renders weekly columns and navigable course blocks", () => {
    const markup = renderToStaticMarkup(
      <MemoryRouter>
        <WeeklyTimetable items={[{ course_id: "course-1", course_code: "HKU101", course_name: "学习设计", weekday: 2, start_time: "10:00", end_time: "12:00", room: "CPD" }]} weekOffset={0} onWeekOffsetChange={() => undefined} title="本周课表" />
      </MemoryRouter>,
    );
    expect(markup).toContain("本周课表");
    expect(markup).toContain("HKU101");
    expect(markup).toContain("学习设计");
    expect(markup).toContain("CPD");
    expect(markup.match(/class="day-column"/g)).toHaveLength(7);
  });
});
