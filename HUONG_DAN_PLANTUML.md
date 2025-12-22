# HƯỚNG DẪN SỬ DỤNG PLANTUML

## 1. Cài đặt PlantUML

### Cách 1: Sử dụng Online Editor
1. Truy cập: https://www.plantuml.com/plantuml/uml/
2. Copy code từ file `diagrams.puml`
3. Paste vào editor và xem kết quả
4. Export sang PNG, SVG, hoặc PDF

### Cách 2: Cài đặt Local
1. **Java** (yêu cầu): Tải từ https://www.java.com/
2. **PlantUML JAR**: Tải từ http://plantuml.com/download
3. **VS Code Extension**: Cài đặt extension "PlantUML" trong VS Code

### Cách 3: Sử dụng với StarUML
1. Mở StarUML
2. File → Import → PlantUML
3. Chọn file `diagrams.puml`
4. Các biểu đồ sẽ được import vào StarUML

## 2. Các biểu đồ trong file

File `diagrams.puml` chứa các biểu đồ sau:

1. **UseCaseDiagram** - Biểu đồ Use Case
2. **ComponentDiagram** - Biểu đồ Component
3. **SequenceChat** - Sequence diagram cho Chat
4. **SequenceMedicineReminder** - Sequence diagram cho Nhắc nhở thuốc
5. **SequenceHealthProfile** - Sequence diagram cho Hồ sơ sức khỏe
6. **ClassDiagram** - Biểu đồ Class
7. **DeploymentDiagram** - Biểu đồ Deployment
8. **ActivityChat** - Biểu đồ Activity cho Chat
9. **StateMachineChat** - Biểu đồ State Machine

## 3. Cách sử dụng từng biểu đồ

### Xem một biểu đồ cụ thể:
```bash
# Sử dụng PlantUML command line
java -jar plantuml.jar diagrams.puml

# Hoặc chỉ render một biểu đồ
java -jar plantuml.jar -tpng -o output diagrams.puml
```

### Trong VS Code:
1. Mở file `diagrams.puml`
2. Nhấn `Alt + D` để preview
3. Hoặc click vào icon PlantUML ở góc trên bên phải

### Trong StarUML:
1. File → Import → PlantUML
2. Chọn file `diagrams.puml`
3. Chọn biểu đồ muốn import
4. Click Import

## 4. Chỉnh sửa biểu đồ

### Thay đổi màu sắc:
```plantuml
skinparam backgroundColor #FFFFFF
skinparam class {
    BackgroundColor #E1F5FF
    BorderColor #0066CC
}
```

### Thay đổi font:
```plantuml
skinparam class {
    FontSize 12
    AttributeFontSize 10
    MethodFontSize 10
}
```

### Thêm ghi chú:
```plantuml
note right of ClassName
    Ghi chú ở đây
end note
```

## 5. Export biểu đồ

### Export sang PNG:
```bash
java -jar plantuml.jar -tpng diagrams.puml
```

### Export sang SVG:
```bash
java -jar plantuml.jar -tsvg diagrams.puml
```

### Export sang PDF:
```bash
java -jar plantuml.jar -tpdf diagrams.puml
```

## 6. Tích hợp vào Markdown

Nếu muốn hiển thị PlantUML trong Markdown, có thể sử dụng:
- **Mermaid** (đã có trong báo cáo)
- **PlantUML Server**: Sử dụng URL từ plantuml.com
- **VS Code Extension**: Preview trực tiếp trong editor

## 7. Tài liệu tham khảo

- PlantUML Official: http://plantuml.com/
- PlantUML Language Reference: http://plantuml.com/guide
- PlantUML Examples: http://plantuml.com/starting

