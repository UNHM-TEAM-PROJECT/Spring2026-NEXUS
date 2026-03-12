## Documentation for changes in `ground_truth.json`
During improving the f1 score of detectors, and testing, some differences were found between the detector outputs and the existing ground truth (GT) values. In some cases, the ground truth did not correctly match the actual content in the syllabus. Because of this, some ground truth entries were updated. This document explains the reasoning behind those updates so that future developers understand why the changes were made.

### Assignment Delivery Detection
- The assignment delivery detector identifies where students are required to submit assignments, typically through learning management systems such as `Canvas` or `MyCourses`. In many syllabi, these platforms are mentioned in multiple contexts, including announcements, course materials, or communication tools.

- During the initial ground truth labeling process, some of these cases were marked as `Canvas`, `MyCourses` because syllabi did talked about the platforms but was not clearly identified whether the platform referred specifically to assignment submission.

- As the detector logic improved to focus on phrases that explicitly indicate submission instructions for example `submit assignments on Canvas`, it became clear that some ground truth entries did not match the actual syllabus content. The ground truth was updated so that platforms are recorded only when they are explicitly used for assignment submission.

### Class Location Detector
- The class location detector identifies where the course takes place, such as `physical classroom locations` or `online platforms` like Zoom or UNH MyCourses. During the ground truth review, some syllabi were labeled with locations even though the syllabus stated `TBD` or did not provide a specific location. In other cases, online courses were labeled with a location even when no platform was mentioned.

- The ground truth was updated to require explicit location information. Only clearly stated room numbers, named platforms, or explicit indicators such as Online are recorded. If the syllabus lists TBD or does not specify a platform, the location is labeled as `Missing`.

### Email Detector
- The email detector extracts instructor email addresses from the syllabus using regular expression patterns that match standard email formats such as name@domain.edu. In some syllabi, the email address existed but the ground truth was labeled as `Missing` because the email appeared inside paragraphs, contact sections, or non‑standard formats but not in the instructor information section that were overlooked during manual labeling.

- When the detector processed these syllabi during evaluation, it correctly extracted the email, but the comparison with the ground truth produced mismatches. The ground truth was updated so that valid instructor emails present in the syllabus are correctly labeled.

### Modality Detector (online_detection)
- The modality detector identifies the course delivery format, such as `in‑person, online, hybrid`, or `asynchronous online`, based on how the syllabus describes course meetings and instruction. It was observed that the label `hybrid` was often used inconsistently. Some courses labeled as hybrid were actually fully online with no in‑person meetings, while others were fully in‑person with optional online resources.

- The ground truth was updated to use modality categories that reflect the actual course structure described in the syllabus. Hybrid is used only when both in‑person and online components are required. Courses without in‑person meetings are labeled as online or asynchronous online, while courses requiring physical attendance are labeled as in‑person. If the syllabus does not clearly describe the delivery format, the modality is labeled as `Missing`.

### Preferred Contact Detector
- The preferred contact method detector identifies the instructor’s preferred way for students to contact them, such as email or phone, when the syllabus explicitly states a preference using phrases like `preferred contact method`, `best way to reach me`, `primary communication method`, or markers such as `preferred`. Previously, the system used a lenient interpretation and assumed that any instructor email listed in the syllabus implied a preferred contact method.

- After manual validation of the syllabus files, it was observed that only a small portion of them actually contained explicit preference indicators. Many syllabi simply listed an email address without stating that it was the preferred way to contact the instructor, so all these are now marked as `Missing`. Additional validation was also added to reduce false positives, including phone validation and context checks to avoid matching unrelated phrases.

### Response Time Detector
- The response time detector identifies statements that describe how quickly instructors respond to student communication, such as “within 24 hours”, “within 48 hours”, or “1–2 business days”. These statements often appear in different natural language forms and are not always written with a clear label like “Response Time”.

- Some of these variations were marked as `Missing` even though a response time policy existed in the syllabus. During testing, the detector successfully identified these phrases using rule‑based pattern matching, which revealed inconsistencies between the detector output and the ground truth. The ground truth was updated to include these valid response time statements.

### SLO Detector
- The SLO detector identifies sections of the syllabus that describe student learning outcomes and course learning objectives. These sections may appear under headings defined as 12 `aaproved titles` in the detector such as `student/program learning outcomes/objectives`, `course learning objectives/outcomes`, `learning objectives/outcomes`, and inside paragraphs explaining what students will learn by the end of the course.

- Because slos structures vary widely, some valid learning outcomes statements were initially labeled as `Missing` in the ground truth even when they appeared within descriptive text of clearly labeled sections, mainly in `learning objectives/outcomes`. The ground truth was updated so that syllabi containing valid learning outcome statements are correct.

### Workload Detection
- The workload detector identifies statements that describe the expected amount of work students must complete for a course, usually expressed as `hours per week` or `total required hours`.

- In many syllabi, the workload section only included the general university credit hour policy rather than describing the actual time students are expected to spend on the course. These policy statements were previously interpreted as valid workload information in the ground truth.

- The ground truth was updated to distinguish between generic credit hour policies and actual course workload expectations. Only course‑specific workload statements are now considered valid workload information, while generic policy statements are labeled as `Missing`.