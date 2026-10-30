# MediQueue – Emergency Patient Management System

MediQueue is a Python-based emergency patient management system that demonstrates priority-based patient scheduling using a **Min-Heap Priority Queue**. Built with Streamlit and SQLite, it helps organize patient registration, waiting queues, treatment status and hospital record management.

## Key Features

- **Dashboard:** Displays total patients, waiting patients, patients in treatment and completed cases.
- **Patient Registration:** Register patients with validated details and triage categories.
- **Live Priority Queue:** Automatically prioritizes patients based on urgency.
- **Patient Records:** Search, filter and view registered patient details.
- **CSV Export:** Export filtered patient records.
- **Analytics:** Visualize patient categories, status distribution, registration trends and summary statistics.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application |
| Streamlit | User interface |
| SQLite | Database management |
| Pandas | Data handling and analytics |
| heapq | Min-heap priority queue |

## Priority Queue Algorithm

MediQueue uses Python's `heapq` module to implement a Min-Heap Priority Queue.

| Triage Category | Priority |
|---|---:|
| Critical | 1 |
| Serious | 2 |
| Moderate | 3 |
| Minor | 4 |

The patient with the smallest priority number is called first. When patients have equal priority, registration time determines the order.

Patient statuses are tracked through three stages:

1. Waiting
2. In Treatment
3. Completed

## Project Structure

```text
MediQueue/
│
├── MediQueue.py
├── hospital.db
├── requirements.txt
└── README.md
```

## Installation and Setup

### 1. Clone the repository

```powershell
git clone YOUR_REPOSITORY_URL
cd MediQueue
```

### 2. Create a virtual environment

```powershell
py -m venv .venv
```

### 3. Activate the environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
py -m pip install -r requirements.txt
```

### 5. Run the application

```powershell
py -m streamlit run MediQueue.py
```

The application will open in your default web browser.

## Future Enhancements

- User authentication and role-based access.
- Multi-user database support.
- Waiting-time estimation.
- Patient notifications.
- Automated testing and deployment.

## Limitations

MediQueue is an academic demonstration project, not a real hospital management or clinical decision-making system. It does not provide medical advice or validated clinical triage. Its manually assigned priority categories are illustrative and must not be used for real medical decisions.

## Contributors

- Vigneshvar K S
- Sharan R
- Sithik P

## Project Type

Academic Mini Project – Data Structures and Algorithms

**Developed using Python, Streamlit and SQLite.**
