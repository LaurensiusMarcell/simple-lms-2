from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Category, Course, Lesson, Enrollment, Progress

# ==============================================================================
# 1. INLINE MODEL CONFIGURATION
# ==============================================================================
class LessonInline(admin.TabularInline):
    """
    Membuat input Materi (Lesson) langsung muncul di dalam halaman Kursus (Course).
    Menggunakan TabularInline agar tampilannya berbentuk tabel horizontal yang ringkas.
    """
    model = Lesson
    extra = 1  # Jumlah baris kosong otomatis yang disediakan untuk materi baru
    fields = ('order', 'title', 'content')
    ordering = ('order',)


# ==============================================================================
# 2. CORE MODELS CONFIGURATION WITH ADVANCED LIST, SEARCH, & FILTER
# ==============================================================================

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # List display yang informatif untuk manajemen pengguna
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active', 'date_joined')
    # Filter cepat berdasarkan Role dan Status Akun
    list_filter = ('role', 'is_staff', 'is_active')
    # Fitur pencarian berdasarkan username dan email
    search_fields = ('username', 'email')
    
    # Memasukkan field kustom 'role' ke dalam tata letak form bawaan Django
    fieldsets = UserAdmin.fieldsets + (
        ('Informasi Akses & Role Simple LMS', {'fields': ('role',)}),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'slug')
    # Otomatis mengisi slug secara realtime ketika mengetik nama kategori
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    list_filter = ('parent',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'category', 'created_at')
    prepopulated_fields = {'slug': ('title',)}
    # Pencarian mendalam (bisa mencari berdasarkan nama instruktur juga via __username)
    search_fields = ('title', 'description', 'instructor__username')
    list_filter = ('category', 'created_at', 'instructor')
    
    # 🌟 PASANG INLINE LESSON DI SINI
    inlines = [LessonInline]

    def get_queryset(self, request):
        # Tetap menggunakan custom manager .for_listing() agar load data di admin super cepat (Anti N+1)
        return super().get_queryset(request).for_listing()


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    """
    Meskipun sudah jadi inline di Course, kita tetap daftarkan menu standalone-nya 
    agar Anda tetap bisa mencari atau memfilter materi secara global jika dibutuhkan.
    """
    list_display = ('order', 'title', 'course')
    list_filter = ('course', 'course__category')
    search_fields = ('title', 'content', 'course__title')
    ordering = ('course', 'order')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'enrolled_at')
    list_filter = ('course', 'enrolled_at')
    search_fields = ('student__username', 'course__title')


@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'lesson', 'is_completed', 'completed_at')
    list_filter = ('is_completed', 'completed_at', 'lesson__course')
    search_fields = ('student__username', 'lesson__title')
    # readonly_fields memastikan admin tidak bisa memanipulasi field completed_at secara ilegal
    readonly_fields = ('completed_at',)