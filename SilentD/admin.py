from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, GeneS, PrimerV, Profile, AMR, MLST, Project, Data, MiSeq

admin.site.unregister(User)

class UserProfileInline(admin.StackedInline):
    model = Profile

class UserProfileAdmin(UserAdmin):
    inlines = [ UserProfileInline, ]

# Register your models here.
admin.site.register(User, UserProfileAdmin)
admin.site.register(GeneS)
admin.site.register(PrimerV)
admin.site.register(AMR)
admin.site.register(MLST)
admin.site.register(Data)
admin.site.register(Project)
admin.site.register(MiSeq)