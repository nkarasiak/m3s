//! Hot-path benchmarks: `cells_in_bbox` per grid (the map-view query) plus
//! `pluscode::children` (largest fan-out). Boxes are sized to yield from a few
//! hundred to a few tens of thousands of cells — the range interactive maps
//! actually request. Numbers are tracked in OPTIMIZATION_PLAN.md.

use criterion::{criterion_group, criterion_main, Criterion};
use std::hint::black_box;
use std::time::Duration;

fn bbox_benches(c: &mut Criterion) {
    let mut g = c.benchmark_group("core");
    g.sample_size(10);
    g.warm_up_time(Duration::from_millis(500));
    g.measurement_time(Duration::from_secs(3));

    // Lyon area, 1°x1° (~85x110 km).
    let (s, w, n, e) = (45.0, 4.0, 46.0, 5.0);

    g.bench_function("geohash_bbox_p5_1deg", |b| {
        b.iter(|| {
            m3s_core::geohash_grid::cells_in_bbox(black_box(s), w, n, e, 5).unwrap()
        })
    });
    g.bench_function("geohash_bbox_p6_1deg", |b| {
        b.iter(|| {
            m3s_core::geohash_grid::cells_in_bbox(black_box(s), w, n, e, 6).unwrap()
        })
    });
    g.bench_function("h3_bbox_r7_1deg", |b| {
        b.iter(|| m3s_core::h3_grid::cells_in_bbox(black_box(s), w, n, e, 7).unwrap())
    });
    g.bench_function("mgrs_bbox_p2_03deg", |b| {
        b.iter(|| {
            m3s_core::mgrs_grid::cells_in_bbox(black_box(s), w, s + 0.3, w + 0.3, 2).unwrap()
        })
    });
    g.bench_function("a5_bbox_r11_1deg", |b| {
        b.iter(|| m3s_core::a5_grid::cells_in_bbox(black_box(s), w, n, e, 11).unwrap())
    });
    g.bench_function("eaquad_bbox_p7_5deg", |b| {
        b.iter(|| {
            m3s_core::eaquad_grid::cells_in_bbox(black_box(s), w, s + 5.0, w + 5.0, 7).unwrap()
        })
    });
    g.bench_function("pluscode_children_400", |b| {
        b.iter(|| m3s_core::pluscode_grid::children(black_box("8F+P6")).unwrap())
    });
    g.finish();
}

criterion_group!(benches, bbox_benches);
criterion_main!(benches);
