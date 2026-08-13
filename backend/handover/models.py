from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.base import BaseModel
from core.user.models import CoreUser, UserGroup
from core.file_management.models import UserMediaFile

class HandoverShift(BaseModel):
    """Model quản lý ca làm việc (shift) trong hệ thống handover"""
    name = models.CharField(max_length=32)
    start_time = models.CharField(max_length=32)  # Format: "HH:MM"
    end_time = models.CharField(max_length=32)  # Format: "HH:MM"
    color = models.CharField(max_length=255, blank=True, null=True)
    
    TRANSLATABLE_FIELDS = ['name']
    
    class Meta:
        ordering = ['id']
        verbose_name = "Handover Shift"
        verbose_name_plural = "Handover Shifts"
    
    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"


class HandoverDocument(BaseModel):
    """Tài liệu handover cho một ca làm việc cụ thể"""
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    handover = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name='handover_documents_as_handover')
    acceptor = models.ManyToManyField(CoreUser, through='HandoverDocumentAcceptor', related_name='handover_documents_as_acceptor')
    shift = models.ForeignKey(HandoverShift, on_delete=models.CASCADE, related_name='handover_documents')
    created_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)
    date_create_shift = models.DateField()  # Ngày tạo ca
    
    class Meta:
        ordering = ['-created_time']
        verbose_name = "Handover Document"
        verbose_name_plural = "Handover Documents"
        indexes = [
            models.Index(fields=['shift']),
            models.Index(fields=['handover']),
            models.Index(fields=['date_create_shift']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"Handover Document {self.id} - {self.shift.name} - {self.date_create_shift}"
    
    def clean(self):
        super().clean()
        if self.start_date >= self.end_date:
            raise ValidationError("end_date must be after start_date")


class HandoverDocumentAcceptor(models.Model):
    """Bảng trung gian cho quan hệ ManyToMany giữa HandoverDocument và User (acceptor)"""
    handover_document = models.ForeignKey(HandoverDocument, on_delete=models.CASCADE, related_name='acceptors')
    acceptor = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name='accepted_handover_documents')
    created_time = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_time']
        verbose_name = "Handover Document Acceptor"
        verbose_name_plural = "Handover Document Acceptors"
        unique_together = [['handover_document', 'acceptor']]
        indexes = [
            models.Index(fields=['handover_document', 'acceptor']),
        ]
    
    def __str__(self):
        return f"{self.handover_document.id} - {self.acceptor.username}"


class HandoverContent(BaseModel):
    """Nội dung chi tiết trong một handover document"""
    handover_doc = models.ForeignKey(HandoverDocument, on_delete=models.CASCADE, related_name='contents')
    content = models.TextField()
    is_notice = models.BooleanField(default=False)
    is_report = models.BooleanField(default=False)
    creator = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name='created_handover_contents')
    created_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)
    editors = models.ManyToManyField(CoreUser, related_name='edited_handover_contents', blank=True)
    
    class Meta:
        ordering = ['-created_time']
        verbose_name = "Handover Content"
        verbose_name_plural = "Handover Contents"
        indexes = [
            models.Index(fields=['handover_doc']),
            models.Index(fields=['creator']),
            models.Index(fields=['is_notice']),
        ]
    
    def __str__(self):
        return f"Content {self.id} - {self.handover_doc.id}"


class HandoverNotice(BaseModel):
    """Thông báo/quan trọng trong hệ thống handover"""
    creator = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name='created_handover_notices')
    content = models.TextField()
    created_time = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)
    user_processed = models.ForeignKey(CoreUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_handover_notices')
    processed_time = models.DateTimeField(null=True, blank=True)
    editors = models.ManyToManyField(CoreUser, related_name='edited_handover_notices', blank=True)
    updated_time = models.DateTimeField(auto_now=True)
    files = models.ManyToManyField(UserMediaFile, related_name='handover_notices', blank=True)
    
    class Meta:
        ordering = ['-created_time']
        verbose_name = "Handover Notice"
        verbose_name_plural = "Handover Notices"
        indexes = [
            models.Index(fields=['creator']),
            models.Index(fields=['is_processed']),
            models.Index(fields=['created_time']),
        ]
    
    def __str__(self):
        return f"Notice {self.id} - {self.creator.username}"


class HandoverNoticeComment(BaseModel):
    """Bình luận trên các thông báo handover, hỗ trợ reply (phân cấp)"""
    notice = models.ForeignKey(HandoverNotice, on_delete=models.CASCADE, related_name='comments')
    writer = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name='handover_notice_comments')
    content = models.TextField()
    updated_time = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    class Meta:
        ordering = ['-updated_time']
        verbose_name = "Handover Notice Comment"
        verbose_name_plural = "Handover Notice Comments"
        indexes = [
            models.Index(fields=['notice']),
            models.Index(fields=['writer']),
            models.Index(fields=['parent']),
        ]
    
    def __str__(self):
        return f"Comment {self.id} - {self.writer.username}"

