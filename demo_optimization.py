import os
import django
from django.db import connection, reset_queries

# 1. Setup environment Django agar script standalone bisa membaca model
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from courses.models import Course

def run_demo():
    print("=" * 60)
    print("        DJANGO ORM QUERY OPTIMIZATION DEMO")
    print("=" * 60)

    # --------------------------------------------------------------------------
    # SKENARIO 1: MASALAH N+1 QUERY (Cek baris demi baris)
    # --------------------------------------------------------------------------
    reset_queries()
    print("\n[💥] MENJALANKAN SKENARIO N+1 (TANPA OPTIMASI)...")
    
    # Query pertama: Mengambil semua kursus
    bad_courses = Course.objects.all()
    
    for course in bad_courses:
        # Menghasilkan sub-query tambahan di setiap perulangan untuk mengambil nama
        _ = course.instructor.username
        _ = course.category.name

    bad_query_count = len(connection.queries)
    print(f"👉 Total query yang dieksekusi: {bad_query_count} query!")
    
    # --------------------------------------------------------------------------
    # SKENARIO 2: OPTIMIZED QUERY (Menggunakan select_related)
    # --------------------------------------------------------------------------
    reset_queries()
    print("\n[✨] MENJALANKAN SKENARIO OPTIMIZED (MENGGUNAKAN MANAGER)...")
    
    # Menggunakan Custom Manager .for_listing() yang mengimplementasikan SQL JOIN
    good_courses = Course.objects.for_listing()
    
    for course in good_courses:
        # Data instruktur dan kategori sudah di-cache di awal, tidak ada query tambahan
        _ = course.instructor.username
        _ = course.category.name

    good_query_count = len(connection.queries)
    print(f"👉 Total query yang dieksekusi: {good_query_count} query!")

    # --------------------------------------------------------------------------
    # 3. KESIMPULAN PERBANDINGAN
    # --------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("                      HASIL PERBANDINGAN")
    print("=" * 60)
    print(f"• Skenario N+1     : {bad_query_count} SQL Queries")
    print(f"• Skenario Optimal : {good_query_count} SQL Query (JOIN)")
    
    if bad_query_count > good_query_count:
        efisiensi = ((bad_query_count - good_query_count) / bad_query_count) * 100
        print(f"🎉 Sukses! Optimasi menghemat database sebesar {efisiensi:.1f}% query.")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    # Pastikan ada data di database agar perulangan berjalan
    if not Course.objects.exists():
        print("[!] Peringatan: Mohon isi minimal 1-2 data Course di Django Admin terlebih dahulu agar demo ini terlihat hasilnya.")
    run_demo()