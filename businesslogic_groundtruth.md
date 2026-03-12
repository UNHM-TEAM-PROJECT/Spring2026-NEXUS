## Documentation for changes in `ground_truth.json`
During improving the f1 score of detectors, and testing, some differences were found between the detector outputs and the existing ground truth (GT) values. In some cases, the ground truth did not correctly match the actual content in the syllabus. Because of this, some ground truth entries were updated. This document explains the reasoning behind those updates so that future developers understand why the changes were made.

### Assignment Delivery Detection
- The assignment delivery detector identifies where students are required to submit assignments, typically through learning management systems such as `Canvas` or `MyCourses`. In many syllabi, these platforms are mentioned in multiple contexts, including announcements, course materials, or communication tools.

- During the initial ground truth labeling process, some of these cases were marked as `Canvas`, `MyCourses` because syllabi did talked about the platforms but was not clearly identified whether the platform referred specifically to assignment submission.

- As the detector logic improved to focus on phrases that explicitly indicate submission instructions for example `submit assignments on Canvas`, it became clear that some ground truth entries did not match the actual syllabus content.

### Assignment Types Detection
- Checked for the most appropriate assignment type header in the document or PDF and verified that there was content under that section describing the kind of work students are expected to complete outside the class assignments.

- Some syllabi were marked as `Missing` because the assignment information appeared under different headers or formats. The ground truth was updated after reviewing these sections so that syllabi containing valid assignment type headers and content are updated.

### Class Location Detector
- The class location detector identifies where the course takes place, such as `physical classroom locations` or `online platforms` like Zoom or UNH MyCourses. During the ground truth review, some syllabi were labeled with locations even though the syllabus stated `TBD` or did not provide a specific location. In other cases, online courses were labeled with a location even when no platform was mentioned.

- The ground truth was updated to require explicit location information. Only clearly stated room numbers, named platforms, or explicit indicators such as Online are recorded. If the syllabus lists TBD or does not specify a platform, the location is labeled as `Missing`.

### Credit Hours Detection
- The credit hours field represents the number of credits assigned to the course. During ground truth review, some syllabus files were labeled as `Missing` even though credit information existed in the document.

- In many cases, the credit value was written using different formats such as cr., credits, or credit hours. The ground truth was updated as `Missing` if none of these keywords are present in the syllabi.

### Deadline Expectation (late_missing_work detector)
- Checked for action verbs and keywords in bulleted lists such as `late, deadlines, late policy, late submission`, and other keywords defined in `late_missing_work_detector.py`.

- If no such title or header was present in the document or PDF, then searched for explicit sentences describing consequences for late submission or penalties. In ground truth some syllabi were labeled as `Missing` even though these policy statements existed in the text.

### Email Detector
- The email detector extracts instructor email addresses from the syllabus using regular expression patterns that match standard email formats such as name@domain.edu. In some syllabi, the email address existed but the ground truth was labeled as `Missing` because the email appeared inside paragraphs, contact sections, or non‑standard formats but not in the instructor information section these were labeled as `Missing` in ground truth.

### Grading Process Detection
- The grading process field represents the section of the syllabus describing how student performance is evaluated. Many entries contained only partial grading information, with only a few lines included while the rest of the grading policy was missing. In some cases, text from the following section of the syllabus was also mistakenly included.

- The ground truth was updated so that the grading process field now contains the complete grading policy as written in the syllabus, including all grading components, percentages, and rules, while excluding unrelated text from other sections.

### Instructor Detector
- The instructor information fields represent the instructor’s name, title, and academic department extracted from the syllabus. Several entries had missing values for the instructor name or title even though this information was clearly present in the syllabus. In addition, some department fields contained extra location information such as UNH Manchester or Manchester appended to the department name.

- The ground truth was updated so that each entry includes the correct instructor name and title whenever they are available in the syllabus. The department field was also corrected to contain only the academic department name.

### Modality Detector (online_detection)
- The modality detector identifies the course delivery format, such as `in‑person, online, hybrid`, or `asynchronous online`, based on how the syllabus describes course meetings and instruction. It was observed that the label `hybrid` was often used inconsistently. Some courses labeled as hybrid were actually fully online with no in‑person meetings, while others were fully in‑person with optional online resources.

- The ground truth was updated to use modality categories that reflect the actual course structure described in the syllabus. Hybrid is used only when both in‑person and online components are required. Courses without in‑person meetings are labeled as online or asynchronous online, while courses requiring physical attendance are labeled as in‑person. If the syllabus does not clearly describe the delivery format, the modality is labeled as `Missing`.

### Preferred Contact Detector
- The preferred contact method detector identifies the instructor’s preferred way for students to contact them, such as email or phone, when the syllabus explicitly states a preference using phrases like `preferred contact method`, `best way to reach me`, `primary communication method`, or markers such as `preferred`. Previously, the system used a lenient interpretation and assumed that any instructor email listed in the syllabus implied a preferred contact method.

- After manual validation of the syllabus files, it was observed that only a small portion of them actually contained explicit preference indicators. Many syllabi simply listed an email address without stating that it was the preferred way to contact the instructor, so all these are now marked as `Missing`. Additional validation was also added to reduce false positives, including phone validation and context checks to avoid matching unrelated phrases.

### Response Time Detector
- The response time detector identifies statements that describe how quickly instructors respond to student communication, such as `within 24 hours`, `within 48 hours`, or `1–2 business days`. These statements often appear in different natural language forms and are not always written with a clear label like `Response Time`.

- Some of these variations were marked as `Missing` even though a response time policy existed in the syllabus.The ground truth was updated to include these valid response time statements.

### SLO Detector
- The SLO detector identifies sections of the syllabus that describe student learning outcomes and course learning objectives. These sections may appear under headings defined as 12 `aaproved titles` in the detector such as `student/program learning outcomes/objectives`, `course learning objectives/outcomes`, `learning objectives/outcomes`, and inside paragraphs explaining what students will learn by the end of the course.

- Because slos structures vary widely, some valid learning outcomes statements were initially labeled as `Missing` in the ground truth even when they appeared within descriptive text of clearly labeled sections, mainly in `learning objectives/outcomes`.

### Workload Detection
- The workload detector identifies statements that describe the expected amount of work students must complete for a course, usually expressed as `hours per week` or `total required hours`.

- In many syllabi, the workload section only included the general university credit hour policy rather than describing the actual time students are expected to spend on the course. These policy statements were previously interpreted as valid workload information in the ground truth.

- The ground truth was updated to distinguish between generic credit hour policies and actual course workload expectations. Only course‑specific workload statements are now considered valid workload information, while generic policy statements are labeled as `Missing`.