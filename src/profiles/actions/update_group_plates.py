class UpdateGroupPlates:
    """
    Class to update group and it's descendants plates
    """

    def __init__(self, group) -> None:
        self.group = group
        super().__init__()

    def update_group_descendants_plates(self):
        groups = self.group.get_descendants(include_self=True)
        for group in groups:
            group.group_plate = group.calculate_group_plate()
            group.save()
