export const ROLES = {
  ADMIN: "admin",
  HEAD_TEACHER: "head_teacher",
  REGISTRAR: "registrar",
  TEACHER: "teacher",
  ACCOUNTANT: "accountant",
  LIBRARIAN: "librarian",
  PARENT: "parent",
  STUDENT: "student",
};

export const ROLE_LABELS = {
  [ROLES.ADMIN]: "System Administrator",
  [ROLES.HEAD_TEACHER]: "Head Teacher",
  [ROLES.REGISTRAR]: "Registrar",
  [ROLES.TEACHER]: "Teacher",
  [ROLES.ACCOUNTANT]: "Accountant",
  [ROLES.LIBRARIAN]: "Librarian",
  [ROLES.PARENT]: "Parent",
  [ROLES.STUDENT]: "Student",
};

export function dashboardPathFor(role) {
  const map = {
    [ROLES.ADMIN]: "/dashboard/admin",
    [ROLES.HEAD_TEACHER]: "/dashboard/head-teacher",
    [ROLES.REGISTRAR]: "/dashboard/registrar",
    [ROLES.TEACHER]: "/dashboard/teacher",
    [ROLES.ACCOUNTANT]: "/dashboard/accountant",
    [ROLES.LIBRARIAN]: "/dashboard/librarian",
    [ROLES.PARENT]: "/dashboard/parent",
    [ROLES.STUDENT]: "/dashboard/student",
  };
  return map[role] || "/dashboard";
}

export function initialsFor(name) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  return parts
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}
