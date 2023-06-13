from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """自定义Model基类:补充基础字段"""

    create_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    update_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    delete_at = models.DateTimeField(null=True, default=None, verbose_name="删除时间")
    note = models.CharField(max_length=255, blank=True, default="", verbose_name="备注")

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.pk)

    def set_delete(self):
        """软删除"""
        self.delete_at = timezone.now()
        self.save()


class Brand(BaseModel):
    name = models.CharField(max_length=255, verbose_name="品牌名称")  # HP or Dell
    mini_sources = models.IntegerField(default=10, verbose_name="爬虫sources")
    mini_count = models.IntegerField(default=10, verbose_name="爬虫产品数量")
    filter_sources = models.IntegerField(default=10, verbose_name="筛选sources")
    filter_count = models.IntegerField(default=10, verbose_name="筛选产品数量")


class ECGood(BaseModel):
    part = models.CharField(
        max_length=255, blank=True, default="", verbose_name="零件号"
    )  # 唯一值，与GSA的mfr_part_no_gsa对应
    mfr_part_no = models.CharField(
        max_length=255, blank=True, default="", verbose_name="制造商零件号"
    )  # ec网页上的
    vendor_part_no = models.CharField(
        max_length=255, blank=True, default="", verbose_name="供应商零件号"
    )  # ec网页上的
    msrp = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, default=0, verbose_name="制造商建议零售价"
    )  # ec网页上的
    federal_govt_spa = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, default=0, verbose_name="联邦政府价格"
    )  # ec网页上的
    ingram_micro_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, default=0, verbose_name="英迈国际价格"
    )  # ingram网页上的
    ec_status = models.BooleanField(null=True, verbose_name="EC爬取状态")
    inm_status = models.BooleanField(null=True, verbose_name="inm爬取状态")


class GSAGood(BaseModel):
    brand_name = models.CharField(max_length=255, verbose_name="品牌名称")
    sin = models.CharField(max_length=255, default="", verbose_name="sin")
    product_name = models.CharField(
        max_length=255, blank=True, default="", verbose_name="产品名称"
    )  # gsa网页上的
    product_description = models.CharField(
        max_length=255, blank=True, default="", verbose_name="产品描述"
    )  # gsa网页上的
    product_description2_strong = models.CharField(
        max_length=255, blank=True, default="", verbose_name="产品描述strong"
    )  # gsa网页上的
    product_description2 = models.CharField(
        max_length=255, blank=True, default="", verbose_name="产品描述2"
    )  # gsa网页上的
    gsa_advantage_price_1 = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, default=0, verbose_name="GSA优势价格1"
    )  # gsa网页上的
    gsa_advantage_price_2 = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, default=0, verbose_name="GSA优势价格2"
    )  # gsa网页上的
    gsa_advantage_price_3 = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, default=0, verbose_name="GSA优势价格3"
    )  # gsa网页上的
    coo = models.CharField(
        max_length=255, blank=True, default="", verbose_name="原产地"
    )  # gsa网页上的
    mfr_part_no_gsa = models.CharField(
        max_length=255, blank=True, default="", verbose_name="制造商零件号"
    )  # gsa网页上的
    gsa_status = models.BooleanField(null=True, verbose_name="GSA爬取状态")
    url = models.CharField(max_length=255, blank=True, default="", verbose_name="url")
    source = models.IntegerField(verbose_name="source")
