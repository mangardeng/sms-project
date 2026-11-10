import { Navigate, Route, Routes } from "react-router-dom";

import AppLayout from "./layouts/AppLayout";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import DashboardPage from "./pages/DashboardPage";
import AcademicCalendarPage from "./pages/academic/AcademicCalendarPage";
import AttendancePage from "./pages/attendance/AttendancePage";
import ClassesPage from "./pages/classes/ClassesPage";
import ExaminationsPage from "./pages/examinations/ExaminationsPage";
import FeesPage from "./pages/fees/FeesPage";
import LibraryPage from "./pages/library/LibraryPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import NotificationsPage from "./pages/notifications/NotificationsPage";
import ParentsPage from "./pages/parents/ParentsPage";
import StudentDetailPage from "./pages/students/StudentDetailPage";
import StudentsPage from "./pages/students/StudentsPage";
import SubjectsPage from "./pages/subjects/SubjectsPage";
import TeachersPage from "./pages/teachers/TeachersPage";
import UsersPage from "./pages/users/UsersPage";
import ProtectedRoute from "./routes/ProtectedRoute";
import RoleRoute from "./routes/RoleRoute";
import { ROLES } from "./utils/roles";

const STAFF_VIEW_ROLES = [
  ROLES.ADMIN,
  ROLES.HEAD_TEACHER,
  ROLES.REGISTRAR,
  ROLES.TEACHER,
  ROLES.PARENT,
  ROLES.STUDENT,
];

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/dashboard/:role" element={<DashboardPage />} />
          <Route path="/change-password" element={<ChangePasswordPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />

          <Route element={<RoleRoute roles={STAFF_VIEW_ROLES} />}>
            <Route path="/students" element={<StudentsPage />} />
            <Route path="/students/:id" element={<StudentDetailPage />} />
            <Route path="/attendance" element={<AttendancePage />} />
            <Route path="/examinations" element={<ExaminationsPage />} />
          </Route>

          <Route
            element={
              <RoleRoute roles={[ROLES.ADMIN, ROLES.HEAD_TEACHER, ROLES.REGISTRAR, ROLES.TEACHER]} />
            }
          >
            <Route path="/teachers" element={<TeachersPage />} />
          </Route>

          <Route element={<RoleRoute roles={[ROLES.ADMIN, ROLES.REGISTRAR]} />}>
            <Route path="/parents" element={<ParentsPage />} />
          </Route>

          <Route
            element={
              <RoleRoute roles={[ROLES.ADMIN, ROLES.HEAD_TEACHER, ROLES.REGISTRAR, ROLES.TEACHER]} />
            }
          >
            <Route path="/classes" element={<ClassesPage />} />
          </Route>

          <Route element={<RoleRoute roles={[ROLES.ADMIN, ROLES.HEAD_TEACHER, ROLES.TEACHER]} />}>
            <Route path="/subjects" element={<SubjectsPage />} />
          </Route>

          <Route element={<RoleRoute roles={[ROLES.ADMIN, ROLES.HEAD_TEACHER]} />}>
            <Route path="/academic-calendar" element={<AcademicCalendarPage />} />
          </Route>

          <Route element={<RoleRoute roles={[ROLES.ADMIN, ROLES.ACCOUNTANT, ROLES.PARENT, ROLES.STUDENT]} />}>
            <Route path="/fees" element={<FeesPage />} />
          </Route>

          <Route
            element={
              <RoleRoute
                roles={[ROLES.ADMIN, ROLES.LIBRARIAN, ROLES.TEACHER, ROLES.PARENT, ROLES.STUDENT]}
              />
            }
          >
            <Route path="/library" element={<LibraryPage />} />
          </Route>

          <Route element={<RoleRoute roles={[ROLES.ADMIN]} />}>
            <Route path="/users" element={<UsersPage />} />
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
