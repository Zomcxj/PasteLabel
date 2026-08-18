"""
数据集分类引擎 - 按 [出现频次 + HBB框大小] 二维KMeans聚类分割

参考: D:/dataset/split_dataset_freq_area/split_freq_area.py

流程:
1. 遍历所有标注，统计每个标签的出现图片数(频次) 和 平均HBB面积
2. 每张图取全局出现次数最少的标签为主标签
3. 对每个标签构建二维特征 [log1p(频次), log1p(平均面积)]，标准化后做KMeans
4. 用轮廓系数(Silhouette)评估并推荐最优K
5. 按输入比例随机拆分train/val（主标签为准，<20张全进train）
6. train/val中，根据图片所有标签的聚类归属分发到对应组
7. 输出到输入文件夹内，生成各组的classes.txt和yaml配置文件
"""
import json
import os
import random
import shutil

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


def get_image_extensions():
    return {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp'}


def load_json_labels_and_boxes(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        labels = set()
        boxes = {}
        for shape in data.get('shapes', []):
            label = shape.get('label', '')
            if not label:
                continue
            labels.add(label)
            if shape.get('shape_type') == 'rectangle':
                pts = shape.get('points', [])
                if len(pts) == 2:
                    w = abs(pts[1][0] - pts[0][0])
                    h = abs(pts[1][1] - pts[0][1])
                    area = w * h
                    boxes.setdefault(label, []).append(area)
        return labels, boxes
    except Exception:
        return set(), {}


def analyze_dataset(image_dir, progress_callback=None, is_interrupted=None):
    image_extensions = get_image_extensions()
    all_files = os.listdir(image_dir)

    images = []
    for file in all_files:
        full_path = os.path.join(image_dir, file)
        if os.path.isdir(full_path):
            continue
        ext = os.path.splitext(file)[1].lower()
        if ext in image_extensions:
            images.append(file)

    label_image_count = {}
    label_total_area = {}
    label_instance_count = {}
    image_labels = {}
    image_primary_label = {}

    total = len(images)
    for idx, image_name in enumerate(images):
        if is_interrupted and is_interrupted():
            return None
        if progress_callback:
            progress_callback(idx + 1, total, None)
        json_path = os.path.join(image_dir, os.path.splitext(image_name)[0] + '.json')
        if not os.path.exists(json_path):
            continue
        labels, boxes = load_json_labels_and_boxes(json_path)
        if not labels:
            continue

        image_labels[image_name] = labels

        for label in labels:
            label_image_count[label] = label_image_count.get(label, 0) + 1
            if label in boxes:
                label_total_area[label] = label_total_area.get(label, 0) + sum(boxes[label])
                label_instance_count[label] = label_instance_count.get(label, 0) + len(boxes[label])

    for image_name, labels in image_labels.items():
        rarest = min(labels, key=lambda l: label_image_count.get(l, 0))
        image_primary_label[image_name] = rarest

    label_mean_area = {}
    for label in label_total_area:
        if label_instance_count.get(label, 0) > 0:
            label_mean_area[label] = label_total_area[label] / label_instance_count[label]

    if label_mean_area:
        fallback_area = float(np.median(list(label_mean_area.values())))
    else:
        fallback_area = 1.0

    mean_areas = {}
    for label in label_image_count:
        if label in label_mean_area:
            mean_areas[label] = label_mean_area[label]
        else:
            mean_areas[label] = fallback_area

    classified_images = {}
    for image_name, label in image_primary_label.items():
        classified_images.setdefault(label, []).append(image_name)

    return (images, label_image_count, mean_areas, image_labels,
            image_primary_label, classified_images)


def build_features(label_image_count, mean_areas):
    labels = sorted(label_image_count.keys())
    freq = np.array([label_image_count[l] for l in labels]).reshape(-1, 1)
    area = np.array([mean_areas[l] for l in labels]).reshape(-1, 1)
    X = np.hstack([np.log1p(freq), np.log1p(area)])
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    return labels, X_scaled, X


def recommend_k(X, max_k=10, progress_callback=None, is_interrupted=None):
    n = X.shape[0]
    if n < 2:
        return 1, {}
    k_max = min(max_k, n - 1)
    k_range = list(range(2, k_max + 1))
    scores = {}
    total = len(k_range)
    for i, k in enumerate(k_range):
        if is_interrupted and is_interrupted():
            return None, {}
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X)
        labels = km.labels_
        if len(set(labels)) > 1:
            sil = float(silhouette_score(X, labels))
        else:
            sil = -1.0
        scores[k] = (sil, float(km.inertia_))
        if progress_callback:
            progress_callback(i + 1, total, k)
    if not scores:
        return 1, {}
    best_k = max(scores, key=lambda k: scores[k][0])
    return best_k, scores


def cluster_labels(X, k, labels):
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(X)
    cluster_of_label = {label: int(cid) for label, cid in zip(labels, kmeans.labels_)}
    centers = kmeans.cluster_centers_

    order = sorted(range(k), key=lambda c: centers[c][1], reverse=True)
    new_id = {old: new for new, old in enumerate(order)}

    group_labels = [set() for _ in range(k)]
    for label, old_cid in cluster_of_label.items():
        group_labels[new_id[old_cid]].add(label)

    return group_labels, kmeans, cluster_of_label


def split_by_class(classified_images, train_ratio, min_threshold=20):
    train_images = []
    val_images = []

    for label, image_list in classified_images.items():
        random.shuffle(image_list)
        count = len(image_list)
        if count < min_threshold:
            if count == 1:
                train_images.extend(image_list)
            else:
                train_images.extend(image_list[:count - 1])
                val_images.append(image_list[count - 1])
        else:
            split_idx = int(count * train_ratio)
            train_images.extend(image_list[:split_idx])
            val_images.extend(image_list[split_idx:])

    return train_images, val_images


def copy_with_trimmed_annotation(src_dir, image_name, dest_dir, allowed_labels):
    image_src = os.path.join(src_dir, image_name)
    if os.path.exists(image_src):
        shutil.copy2(image_src, dest_dir)

    json_src = os.path.join(src_dir, os.path.splitext(image_name)[0] + '.json')
    if not os.path.exists(json_src):
        return

    with open(json_src, 'r', encoding='utf-8') as f:
        data = json.load(f)

    data['shapes'] = [
        shape for shape in data.get('shapes', [])
        if shape.get('label', '') in allowed_labels
    ]

    json_dst = os.path.join(dest_dir, os.path.splitext(image_name)[0] + '.json')
    with open(json_dst, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def write_classes_txt(path, labels):
    with open(path, 'w', encoding='utf-8') as f:
        for label in sorted(labels):
            f.write(label + '\n')


def write_yaml(path, dataset_root, train_rel, val_rel, labels):
    sorted_labels = sorted(labels)
    lines = [
        f"# Ultralytics AGPL-3.0 License",
        f"#",
        f"# Train/val sets",
        f"path: {dataset_root}",
        f"train: {train_rel}",
        f"val: {val_rel}",
        f"test: ",
        f"",
        f"# Classes",
        f"names:",
    ]
    for i, label in enumerate(sorted_labels):
        lines.append(f"  {i}: {label}")
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def classify_and_split(image_dir, train_ratio, k, analysis=None,
                       progress_callback=None, is_interrupted=None, log_fn=None):
    """完整分类 + 分割流水线。

    analysis 可传入已分析结果（避免重复分析），格式同 analyze_dataset 返回值。
    """
    if analysis is None:
        analysis = analyze_dataset(image_dir, progress_callback, is_interrupted)
        if analysis is None:
            return None
    (images, label_image_count, mean_areas, image_labels,
     image_primary_label, classified_images) = analysis

    if not images:
        return None

    labels, X_scaled, X = build_features(label_image_count, mean_areas)
    if len(labels) < 2:
        return None

    group_labels, kmeans, cluster_of_label = cluster_labels(X_scaled, k, labels)

    train_images, val_images = split_by_class(classified_images, train_ratio)

    group_dirs = []
    for gi in range(k):
        train_dir = os.path.join(image_dir, f'g{gi}', 'train', 'images')
        val_dir = os.path.join(image_dir, f'g{gi}', 'val', 'images')
        for d in [train_dir, val_dir]:
            os.makedirs(d, exist_ok=True)
        group_dirs.append((train_dir, val_dir))

    group_train_count = [0] * k
    group_val_count = [0] * k

    copy_tasks = []
    for gi in range(k):
        for image_name in train_images:
            if image_labels.get(image_name, set()) & group_labels[gi]:
                copy_tasks.append((image_name, gi, 'train'))
        for image_name in val_images:
            if image_labels.get(image_name, set()) & group_labels[gi]:
                copy_tasks.append((image_name, gi, 'val'))
    total = len(copy_tasks)
    for idx, (image_name, gi, split_kind) in enumerate(copy_tasks):
        if is_interrupted and is_interrupted():
            return None
        dest_dir = group_dirs[gi][0] if split_kind == 'train' else group_dirs[gi][1]
        if split_kind == 'train':
            group_train_count[gi] += 1
        else:
            group_val_count[gi] += 1
        copy_with_trimmed_annotation(image_dir, image_name, dest_dir, group_labels[gi])
        if progress_callback:
            progress_callback(idx + 1, total, None)

    folder_name = os.path.basename(os.path.normpath(image_dir))
    for gi in range(k):
        write_classes_txt(os.path.join(image_dir, f'g{gi}', 'classes.txt'), group_labels[gi])
        write_yaml(os.path.join(image_dir, f'{folder_name}_g{gi}.yaml'),
                   image_dir, f'g{gi}/train/images', f'g{gi}/val/images', group_labels[gi])

    if log_fn:
        log_fn(f"train: {len(train_images)}, val: {len(val_images)}")

    return {
        'images': images,
        'label_image_count': label_image_count,
        'mean_areas': mean_areas,
        'image_labels': image_labels,
        'image_primary_label': image_primary_label,
        'classified_images': classified_images,
        'group_labels': group_labels,
        'k': k,
        'train_images': train_images,
        'val_images': val_images,
        'group_train_count': group_train_count,
        'group_val_count': group_val_count,
        'output_dir': image_dir,
    }
