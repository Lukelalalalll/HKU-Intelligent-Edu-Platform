import { describe, expect, it } from 'vitest';
import { academicYearStartFor, getAcademicYears, semesterFor } from '../courseTerms';

describe('course term boundaries', () => {
  it('uses the three HKU-style semesters and the January preselection', () => {
    expect(semesterFor(new Date(2026, 8, 1))).toBe('semester_1');
    expect(semesterFor(new Date(2026, 11, 31))).toBe('semester_1');
    expect(semesterFor(new Date(2027, 0, 1))).toBe('semester_2');
    expect(semesterFor(new Date(2027, 1, 1))).toBe('semester_2');
    expect(semesterFor(new Date(2027, 4, 31))).toBe('semester_2');
    expect(semesterFor(new Date(2027, 5, 1))).toBe('summer');
    expect(semesterFor(new Date(2027, 7, 31))).toBe('summer');
  });

  it('keeps September as the academic year boundary', () => {
    expect(academicYearStartFor(new Date(2026, 8, 1))).toBe(2026);
    expect(academicYearStartFor(new Date(2027, 0, 1))).toBe(2026);
  });

  it('includes the current year and sorts previous years descending', () => {
    const courses = [
      { academic_year_start: 2024 },
      { academic_year_start: 2026 },
      { academic_year_start: 2025 },
    ] as never;
    expect(getAcademicYears(courses, new Date(2026, 8, 1))).toEqual([2026, 2025, 2024]);
  });
});

