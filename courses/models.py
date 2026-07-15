from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db.models import Count, Q, ExpressionWrapper, FloatField
from django.utils import timezone

# ==============================================================================
# 1. USER MODEL (Kustom dengan Sistem Role)
# ==============================================================================
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        INSTRUCTOR = 'INSTRUCTOR', 'Instructor'
        STUDENT = 'STUDENT', 'Student'

    role = models.CharField(
        max_length=15,
        choices=Role.choices,
        default=Role.STUDENT
    )

    class Meta:
        indexes = [
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


# ==============================================================================
# 2. CATEGORY MODEL (Self-referencing untuk Hierarchy)
# ==============================================================================
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcategories'
    )

    class Meta:
        verbose_name_plural = "Categories"
        indexes = [
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return f"{self.parent.name} -> {self.name}" if self.parent else self.name


# ==============================================================================
# CUSTOM QUERYSET & MANAGER FOR COURSE
# ==============================================================================
class CourseQuerySet(models.QuerySet):
    def for_listing(self):
        """
        Mengoptimalkan query untuk halaman list view.
        Menggunakan select_related untuk mengambil data instructor dan category 
        dalam 1 query JOIN tunggal (Mencegah masalah N+1 Query).
        """
        return self.select_related('instructor', 'category')

class CourseManager(models.Manager):
    def get_queryset(self):
        return CourseQuerySet(self.model, using=self._db)
        
    def for_listing(self):
        return self.get_queryset().for_listing()


# ==============================================================================
# 3. COURSE MODEL
# ==============================================================================
class Course(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    instructor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='conducted_courses',
        limit_choices_to={'role': User.Role.INSTRUCTOR}
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='courses'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Daftarkan Custom Manager ke Model Course
    objects = CourseManager()

    class Meta:
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.title


# ==============================================================================
# 4. LESSON MODEL (Materi Kursus)
# ==============================================================================
class Lesson(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons'
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    order = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Urutan posisi materi (dimulai dari angka 1)"
    )

    class Meta:
        ordering = ['order']
        # Menggunakan UniqueConstraint modern menggantikan unique_together
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'order'],
                name='unique_course_lesson_order'
            )
        ]

    def __str__(self):
        return f"[{self.order}] {self.title} ({self.course.title})"


# ==============================================================================
# CUSTOM QUERYSET & MANAGER FOR ENROLLMENT
# ==============================================================================
class EnrollmentQuerySet(models.QuerySet):
    def for_student_dashboard(self, student_user):
        """
        Mengoptimalkan query untuk dashboard siswa dengan kalkulasi progres agregat.
        """
        return self.filter(student=student_user)\
            .select_related('course', 'course__instructor')\
            .annotate(
                total_lessons=Count('course__lessons', distinct=True),
                completed_lessons=Count(
                    'course__lessons__progress_records',
                    filter=Q(
                        course__lessons__progress_records__student=student_user,
                        course__lessons__progress_records__is_completed=True
                    ),
                    distinct=True
                )
            ).annotate(
                progress_percentage=ExpressionWrapper(
                    Q(total_lessons__gt=0) * (models.F('completed_lessons') * 100.0 / models.F('total_lessons')),
                    output_field=FloatField()
                )
            )

class EnrollmentManager(models.Manager):
    def get_queryset(self):
        return EnrollmentQuerySet(self.model, using=self._db)
        
    def for_student_dashboard(self, student_user):
        return self.get_queryset().for_student_dashboard(student_user)


# ==============================================================================
# 5. ENROLLMENT MODEL
# ==============================================================================
class Enrollment(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='enrollments',
        limit_choices_to={'role': User.Role.STUDENT}
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    # Daftarkan Custom Manager ke Model Enrollment
    objects = EnrollmentManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'course'],
                name='unique_student_course_enrollment'
            )
        ]

    def __str__(self):
        return f"{self.student.username} terdaftar di {self.course.title}"


# ==============================================================================
# 6. PROGRESS MODEL (Tracking Status Penyelesaian Materi Kelas)
# ==============================================================================
class Progress(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lesson_progress',
        limit_choices_to={'role': User.Role.STUDENT}
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='progress_records'
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Progress Records"
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'lesson'],
                name='unique_student_lesson_progress'
            )
        ]

    def save(self, *args, **kwargs):
        """Otomatis mengisi completed_at saat status diubah menjadi Selesai"""
        if self.is_completed and not self.completed_at:
            self.completed_at = timezone.now()
        elif not self.is_completed:
            self.completed_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        status = "Selesai" if self.is_completed else "Belum Selesai"
        return f"{self.student.username} - {self.lesson.title} ({status})"