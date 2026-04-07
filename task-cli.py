import argparse
import json
import os
import sys
from datetime import datetime, timezone

DATA_FILE = os.path.join(os.path.dirname(__file__), "tasks.json")
VALID_STATUSES = {"todo", "in-progress", "done"}


def ensure_data_file_exists() -> None:
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)


def load_tasks() -> list[dict]:
    ensure_data_file_exists()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            print("Warning: tasks.json does not contain a list. Using empty list.", file=sys.stderr)
            return []
    except json.JSONDecodeError:
        print("Warning: tasks.json is invalid JSON. Using empty list.", file=sys.stderr)
        return []
    except OSError as e:
        print(f"Error reading tasks file: {e}", file=sys.stderr)
        return []


def save_tasks(tasks: list[dict]) -> None:
    temp_file = DATA_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)
    os.replace(temp_file, DATA_FILE)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def to_local_time(iso_utc: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return "invalid-date"


def generate_id(tasks: list[dict]) -> int:
    ids = [task.get("id") for task in tasks if isinstance(task.get("id"), int)]
    return (max(ids) + 1) if ids else 1


def find_task(tasks: list[dict], task_id: int) -> dict | None:
    for task in tasks:
        if task.get("id") == task_id:
            return task
    return None


def add_task(tasks: list[dict], description: str) -> None:
    description = description.strip()
    if not description:
        print("Task description cannot be empty.")
        return

    now = now_utc_iso()
    task = {
        "id": generate_id(tasks),
        "description": description,
        "status": "todo",
        "createdAt": now,
        "updatedAt": now,
    }
    tasks.append(task)
    save_tasks(tasks)
    print(f"Task added successfully (ID: {task['id']})")


def delete_task(tasks: list[dict], task_id: int) -> None:
    task = find_task(tasks, task_id)
    if not task:
        print(f"Task #{task_id} not found")
        return

    tasks.remove(task)
    save_tasks(tasks)
    print(f"Deleted task #{task['id']}: {task['description']}")


def update_task(tasks: list[dict], task_id: int, new_description: str) -> None:
    task = find_task(tasks, task_id)
    if not task:
        print(f"Task #{task_id} not found")
        return

    new_description = new_description.strip()
    if not new_description:
        print("New task description cannot be empty.")
        return

    old_desc = task.get("description", "")
    task["description"] = new_description
    task["updatedAt"] = now_utc_iso()
    save_tasks(tasks)
    print(f"Updated task: #{task['id']} {old_desc} => #{task['id']} {new_description}")


def update_task_status(tasks: list[dict], task_id: int, new_status: str) -> None:
    if new_status not in VALID_STATUSES:
        print(f"Invalid status: {new_status}")
        return

    task = find_task(tasks, task_id)
    if not task:
        print(f"Task #{task_id} not found")
        return

    task["status"] = new_status
    task["updatedAt"] = now_utc_iso()
    save_tasks(tasks)
    print(f"Updated task status. Task #{task_id} {task['description']} status is {task['status']}")


def print_tasks_list(tasks: list[dict], status_filter: str | None = None) -> None:
    if not tasks:
        print("Task list is empty, add your first task using add \"task description\" command")
        return

    found = False
    for task in tasks:
        if status_filter is None or task.get("status") == status_filter:
            print(
                f"#{task.get('id')} [{task.get('status')}] {task.get('description')} | "
                f"created: {to_local_time(task.get('createdAt', ''))} | "
                f"updated: {to_local_time(task.get('updatedAt', ''))}"
            )
            found = True

    if not found:
        print("Tasks not found")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="task-cli",
        description="Task Tracker CLI",
    )
    subparser = parser.add_subparsers(dest="command", required=True)

    add_parser = subparser.add_parser("add", help="Add new task")
    add_parser.add_argument("description", help="Task description")

    delete_parser = subparser.add_parser("delete", help="Delete task")
    delete_parser.add_argument("id", type=int, help="Task ID to delete")

    update_parser = subparser.add_parser("update", help="Update task description")
    update_parser.add_argument("id", type=int, help="Task ID to update")
    update_parser.add_argument("description", help="New task description")

    mark_todo_parser = subparser.add_parser("mark-todo", help="Mark task as todo")
    mark_todo_parser.add_argument("id", type=int, help="Task ID to mark as todo")

    mark_progress_parser = subparser.add_parser("mark-in-progress", help="Mark task as in-progress")
    mark_progress_parser.add_argument("id", type=int, help="Task ID to mark as in-progress")

    mark_done_parser = subparser.add_parser("mark-done", help="Mark task as done")
    mark_done_parser.add_argument("id", type=int, help="Task ID to mark as done")

    list_parser = subparser.add_parser("list", help="List tasks")
    list_parser.add_argument(
        "status",
        nargs="?",
        default=None,
        choices=["todo", "in-progress", "done"],
        help="Optional filter: todo, in-progress, done",
    )

    return parser


def main() -> None:
    tasks = load_tasks()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "add":
        add_task(tasks, args.description)
    elif args.command == "delete":
        delete_task(tasks, args.id)
    elif args.command == "update":
        update_task(tasks, args.id, args.description)
    elif args.command == "mark-todo":
        update_task_status(tasks, args.id, "todo")
    elif args.command == "mark-in-progress":
        update_task_status(tasks, args.id, "in-progress")
    elif args.command == "mark-done":
        update_task_status(tasks, args.id, "done")
    elif args.command == "list":
        print_tasks_list(tasks, args.status)


if __name__ == "__main__":
    main()