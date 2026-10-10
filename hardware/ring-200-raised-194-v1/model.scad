// Dimensions in millimeters. Total height: 6 mm.
$fn = 1024;
base_od = 200; base_id = 188; base_t = 2;
wall_od = 195; wall_id = 191; wall_h = 4;
rotate_extrude() polygon([
 [base_id/2,0], [base_od/2,0], [base_od/2,base_t],
 [wall_od/2,base_t], [wall_od/2,base_t+wall_h],
 [wall_id/2,base_t+wall_h], [wall_id/2,base_t], [base_id/2,base_t]
]);
