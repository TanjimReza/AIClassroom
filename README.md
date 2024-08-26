# AI Classroom

AI Classroom is a Django-based web application designed to facilitate online learning environments. It provides features for user authentication, classroom management, and user role-based access control.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Project Structure](#project-structure)
- [Authentication](#authentication)
- [Contributing](#contributing)
- [License](#license)

## Features

- User authentication (login, logout, password reset)
- User roles (General Admin, Class Admin, Teacher, Student)
- Classroom creation and management
- Responsive design using Tailwind CSS

## Prerequisites

- Python 3.12.3 or higher
- pip (Python package manager)
- Git (version control)

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd AIClassroom
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```
     source venv/bin/activate
     ```

4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Configuration

1. Create a `.env` file in the project root and add the following:
   ```
   SECRET_KEY=your_secret_key_here
   DEBUG=True
   ```

2. Update the database settings in `AIClassroom/settings.py` if needed.

## Running the Application

1. Apply database migrations:
   ```
   python manage.py migrate
   ```

2. Create a superuser:
   ```
   python manage.py createsuperuser
   ```

3. Run the development server:
   ```
   python manage.py runserver
   ```

4. Access the application at `http://127.0.0.1:8000/`

## Project Structure

- `AIClassroom/`: Main project directory
- `home/`: Main application directory
- `templates/`: HTML templates
- `static/`: Static files (CSS, JavaScript, images)
- `manage.py`: Django management script

## Authentication

The project uses Django's built-in authentication system with custom user models. Password reset functionality is implemented using Django's PasswordResetView.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.