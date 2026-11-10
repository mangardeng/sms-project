import { ROLES } from "../utils/roles";

const A = ROLES.ADMIN,
  HT = ROLES.HEAD_TEACHER,
  R = ROLES.REGISTRAR,
  T = ROLES.TEACHER,
  AC = ROLES.ACCOUNTANT,
  L = ROLES.LIBRARIAN,
  P = ROLES.PARENT,
  S = ROLES.STUDENT;

/**
 * Each entry: { to, label, roles }. `roles: null` means visible to everyone.
 */
export const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", roles: null },
  { to: "/students", label: "Students", roles: [A, HT, R, T, P, S] },
  { to: "/teachers", label: "Teachers", roles: [A, HT, R, T] },
  { to: "/parents", label: "Parents", roles: [A, R] },
  { to: "/classes", label: "Classes", roles: [A, HT, R, T] },
  { to: "/subjects", label: "Subjects", roles: [A, HT, T] },
  { to: "/academic-calendar", label: "Academic Calendar", roles: [A, HT] },
  { to: "/attendance", label: "Attendance", roles: [A, HT, T, P, S] },
  { to: "/examinations", label: "Examinations", roles: [A, HT, T, P, S] },
  { to: "/fees", label: "Fees", roles: [A, AC, P, S] },
  { to: "/library", label: "Library", roles: [A, L, T, P, S] },
  { to: "/notifications", label: "Notifications", roles: null },
  { to: "/users", label: "User Accounts", roles: [A] },
];

export function navItemsForRole(role) {
  return NAV_ITEMS.filter((item) => !item.roles || item.roles.includes(role));
}
