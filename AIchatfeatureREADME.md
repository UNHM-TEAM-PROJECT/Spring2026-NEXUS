## AI Chat Feature Implementation README
Created by: Swathi Danturi, Team NEXUS Spring 2026

### Introduction
- Sometimes a syllabus does not include the all the necessary information and this information is important because it tells students how to understand the syllabus and course better.

- To handle this situation, the backend checks whether the necessary information exists in the uploaded syllabus. If it is missing, the system asks the user to provide it. The backend then generates a template document containing the provided information.

- As a proof of concept, this feature is implemented for now by taking into consideration on the best performing checker, which is `preferred_contact_method`.

### Syllabus Uploading and Processing
- When a syllabus file is uploaded, it is processed by the backend through the `/upload` endpoint defined in `api_routes.py`.
- The uploaded file is handled inside the function `_process_single_file()`. In this step:
    - The file name is captured using file.filename
    - The document text is extracted
    - Multiple detectors run to find syllabus information
- One of the detectors used is PreferredDetector from `detectors/preferred_contact_detector.py`.
- This detector checks whether the syllabus mentions the instructor’s preferred contact method.

### Detecting Missing Preferred Contact Method
- After the detector runs, the backend checks the result stored in `["preferred_information"]`
- If the preferred contact method is not found, the system sets `preferred_contact_missing = True`
- This value is returned in the response from the `/upload` endpoint, so the frontend knows that the user must provide the missing information.

### Storing Uploaded Filename
- When the syllabus is uploaded, the filename is stored in a variable called `last_uploaded_filename`
- This variable is stored in `api_routes.py` so the system can later include the filename in the generated template.
- This ensures the generated template shows which syllabus file the information belongs to.

### Template Generation
- The system uses a template file called `syllabus_template.txt`
- The template contains placeholders such as `{{filename}}`, `{{preferred_contact_method}}`
- The template is processed using the function `generate_template()` located in `template_generator.py`
- This function reads the template file and replaces the placeholders with actual values.

### Submitting the preferred_contact_method
- When the preferred contact method is missing, the user sends the value to the backend through the endpoint `/submit_preferred_contact`
- This endpoint is implemented in api_routes.py inside the function `submit_preferred_contact()`
- The endpoint receives the user input and sends it to the template generator along with the stored filename.

### Template Output
- After processing the template, the backend generates a text document that includes: the uploaded syllabus file name, the preferred contact method provided by the user
- The completed template is then returned to the user as a downloadable text file.

### Testing with Python Scripts
- The backend was also tested using two Python scripts: `test_upload.py`, `test_api.py`
**test_upload.py**
This script tests the `/upload` endpoint by sending a syllabus file. It verifies that:
- File upload works correctly
- Detectors run successfully
- Missing preferred contact method is identified

**test_api.py**
This script tests the `/submit_preferred_contact` endpoint by sending the preferred contact method. It verifies that:
- User input is accepted
- Template is generated correctly
- Filename and preferred contact method appear in the output

### Testing with Postman
#### Step 1 - Upload Syllabus
- A `POST` request is sent to `/upload`
- This runs `_process_single_file()` and the PreferredDetector.
- If the preferred contact method is missing, the response contains `preferred_contact_missing = true`

#### Step 2 - Submit preferred_contact_method
- A second `POST` request is sent to `/submit_preferred_contact`
- This endpoint calls `generate_template()` to create the completed template using the provided value.