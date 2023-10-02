from excel_export.styles import ExcelBaseStyles


class QuequicomStyles(ExcelBaseStyles):

    def set_columns_width(self):
        columns_width = [25, 25, 20, 20, 20, 20, 20, 65, 65, 65, 65, 45, 25, 25, 25, 10, 25, 25, 25, 25, 25, 50, 50,
                         20, 20, 50, 50, 20, 20, 20, 20, 230, 50, 100, 25, 230, 15, 15, 15]
        for _ in range(self.max_features):
            columns_width += [30, 50]
        return columns_width


class EntriesStyles(ExcelBaseStyles):

    def set_columns_width(self):
        return [30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30]


class ClosedRecordsStyles(ExcelBaseStyles):

    def set_columns_width(self):
        return [30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30]


class ThemesRankingStyles(ExcelBaseStyles):

    def set_columns_width(self):
        return 30


class ApplicantsRecordCountStyles(ExcelBaseStyles):

    def set_columns_width(self):
        return [50, 20, 10]


class RecordStateGroupsStyles(ExcelBaseStyles):

    def set_columns_width(self):
        return [35, 20, 20, 20, 20, 20, 20, 20]


class OperatorsStyles(ExcelBaseStyles):

    def set_columns_width(self):
        return [35, 20, 20, 20, 25, 35, 35]
