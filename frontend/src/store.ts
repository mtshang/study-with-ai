import { useEffect, useState } from "react";
import { now, seedWorkspace, uid } from "./data";
import type { UpdateCourse, Workspace } from "./types";

const KEY = "study-with-ai:prototype:v1";
function read(): Workspace {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (
        parsed.version === 1 &&
        Array.isArray(parsed.courses) &&
        parsed.settings &&
        typeof parsed.activeCourseId === "string" &&
        parsed.courses.every((c: Record<string, unknown>) =>
          [
            "chapters",
            "exercises",
            "assignments",
            "submissions",
            "materials",
            "messages",
            "events",
            "revisions",
          ].every((key) => Array.isArray(c[key])),
        )
      )
        return {
          ...parsed,
          settings: {
            ...parsed.settings,
            fontOffset:
              Number.isInteger(parsed.settings.fontOffset) &&
              parsed.settings.fontOffset >= 0 &&
              parsed.settings.fontOffset <= 6
                ? parsed.settings.fontOffset
                : 3,
          },
        };
    }
  } catch {
    /* Invalid or unavailable storage: open a clean demo without crashing. */
  }
  return seedWorkspace();
}
export function useWorkspace() {
  const [state, setState] = useState<Workspace>(read);
  const [storageError, setStorageError] = useState(false);
  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
      setStorageError(false);
    } catch {
      setStorageError(true);
    }
  }, [state]);
  const updateCourse: UpdateCourse = (id, update, event) =>
    setState((previous) => ({
      ...previous,
      courses: previous.courses.map((course) => {
        if (course.id !== id) return course;
        const next = update(course);
        return event
          ? {
              ...next,
              events: [{ id: uid(), time: now(), ...event }, ...next.events],
            }
          : next;
      }),
    }));
  return { state, setState, updateCourse, storageError };
}
