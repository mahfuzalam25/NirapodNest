from django.urls import path


from .views import ChangePasswordView, EditProfileView, MyProfileView, PublicProfileView, RegisterUserView, ResetPasswordConfirmView, UploadAvatarView, VerifyOTPView, CompleteProfileView, UserProfileView, LoginUserView,RequestPasswordResetOTPView, VerifyResetOTPView

urlpatterns = [
    path('signup/', RegisterUserView.as_view(), name='signup'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('login/', LoginUserView.as_view(), name='login'),
    path('complete-profile/', CompleteProfileView.as_view(), name='complete-profile'),
    path('profile/<uuid:uid>/', UserProfileView.as_view(), name='user-profile'),
    path('profile/me/', MyProfileView.as_view(), name='my-profile'),
    path('profile/avatar/', UploadAvatarView.as_view(), name='upload-avatar'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('profile/edit/', EditProfileView.as_view(), name='edit-profile'),
    path('profile/public/<uuid:uid>/', PublicProfileView.as_view(), name='public-profile'),

    path('password-reset/request/', RequestPasswordResetOTPView.as_view(), name='password_reset_request'),
    path('password-reset/verify/', VerifyResetOTPView.as_view(), name='password_reset_verify'),
    path('password-reset/confirm/', ResetPasswordConfirmView.as_view(), name='password_reset_confirm'),   
]