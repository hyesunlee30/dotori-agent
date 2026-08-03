# Backend Conversion Skill: Node.js/Express to Spring Boot 3.3

## Overview

This skill defines the conversion rules for transforming Node.js/Express + MongoDB (Mongoose) backend code to Spring Boot 3.3 with Layered+Domain DDD architecture.

## Express Router to Spring Controller Mapping

### URL Routing

| Express | Spring Boot |
|---------|-------------|
| `GET /api/evaluations` | `@GetMapping("/evaluations")` |
| `POST /api/evaluations` | `@PostMapping("/evaluations")` |
| `PUT /api/evaluations/:id` | `@PutMapping("/evaluations/{id}")` |
| `DELETE /api/evaluations/:id` | `@DeleteMapping("/evaluations/{id}")` |
| `GET /api/evaluations/stats` | `@GetMapping("/evaluations/stats")` |

### Parameter Mapping

| Express | Spring Boot |
|---------|-------------|
| `req.params.id` | `@PathVariable String id` |
| `req.body` | `@RequestBody EvaluationDto.Request` |
| `req.query.page` | `@RequestParam(defaultValue = "1") int page` |
| `req.query.search` | `@RequestParam(required = false) String searchText` |

### Response Mapping

| Express | Spring Boot |
|---------|-------------|
| `res.json({ success: true, data: ... })` | `ResponseEntity.ok(ApiResponse.success(...))` |
| `res.status(500).json({ success: false, message: ... })` | `ResponseEntity.status(500).body(ApiResponse.error(...))` |

### API Documentation Pattern

Controller implementation must separate API documentation into a dedicated interface:

```java
// EvaluationControllerApiDoc.java
public interface EvaluationControllerApiDoc {
    @Operation(summary = "평가 목록 조회")
    @ApiResponses({ @ApiResponse(responseCode = "200", description = "조회 성공") })
    ResponseEntity<ApiResponse<PageResponse<EvaluationDto.Response>>> getEvaluations(
        @Parameter(description = "페이지 번호") @RequestParam(defaultValue = "1") int page,
        @Parameter(description = "페이지 크기") @RequestParam(defaultValue = "10") int size,
        @Parameter(description = "검색어") @RequestParam(required = false) String searchText
    );
}

// EvaluationController.java
@RestController
@RequestMapping("/api/evaluations")
@RequiredArgsConstructor
public class EvaluationController implements EvaluationControllerApiDoc {
    private final EvaluationService evaluationService;
    // Implementation without annotation duplication
}
```

## Mongoose Schema to JPA Entity Mapping

### Field Type Mapping

| Mongoose Type | Java/JPA |
|---------------|----------|
| `type: String, required: true` | `@Column(nullable = false)` |
| `type: String, maxlength: 200` | `@Column(length = 200, nullable = false)` |
| `type: Number, min: 1, max: 100` | `@Column @Min(1) @Max(100)` |
| `type: Date` | `@Column(nullable = false) private LocalDateTime createdAt` |
| `type: [String]` | `@ElementCollection @Column(nullable = false)` |
| `enum: ['draft', 'submitted', 'completed']` | `@Enumerated(EnumType.STRING)` |
| `ref: 'OtherModel'` | `@ManyToOne @JoinColumn(name = "other_id")` |

### Mongoose Schema Example

```javascript
const evaluationSchema = new mongoose.Schema({
  title: { type: String, required: [true, '제목을 입력해주세요'], trim: true, maxlength: 200 },
  category: { type: String, required: true, enum: ['역량', '성과', '태도', '전문성'] },
  score: { type: Number, required: true, min: 1, max: 100 },
  status: { type: String, enum: ['draft', 'submitted', 'completed'], default: 'draft' },
  evaluator: { type: String, required: true },
  evaluatee: { type: String, required: true },
  createdAt: { type: Date, default: Date.now },
  updatedAt: { type: Date, default: Date.now },
});
evaluationSchema.index({ evaluator: 1, evaluatee: 1, category: 1 });
evaluationSchema.index({ createdAt: -1 });
evaluationSchema.index({ status: 1 });
```

### Converted JPA Entity

```java
@Entity
@Table(name = "evaluations")
@RequiredArgsConstructor
public class Evaluation extends BaseEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private String id;

    @Column(nullable = false, length = 200)
    private String title;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Category category;

    @Column(nullable = false)
    @Min(1)
    @Max(100)
    private Integer score;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private EvaluationStatus status;

    @Column(nullable = false)
    private String evaluator;

    @Column(nullable = false)
    private String evaluatee;

    public enum Category {
        역량, 성과, 태도, 전문성, 커뮤니케이션, 리더십, 문제해결력, 팀워크
    }

    public enum EvaluationStatus {
        draft, submitted, completed
    }
}
```

### BaseEntity (Audit Fields)

```java
@MappedSuperclass
@RequiredArgsConstructor
public abstract class BaseEntity {

    @CreatedDate
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column(nullable = false)
    private LocalDateTime updatedAt;

    @CreatedBy
    @Column(nullable = false, updatable = false)
    private String createdBy;

    @LastModifiedBy
    @Column(nullable = false)
    private String updatedBy;
}
```

## Controller Logic to Spring Service Mapping

### CRUD Operations

| Express Controller | Spring Service |
|--------------------|----------------|
| `await Evaluation.find(query)` | `evaluationRepository.findAll(specification)` |
| `await Evaluation.findById(id)` | `evaluationRepository.findById(id)` |
| `await new Evaluation(body).save()` | `evaluationRepository.save(entity)` |
| `await Evaluation.findByIdAndUpdate(id, update)` | `evaluationRepository.save(entity)` |
| `await Evaluation.findByIdAndDelete(id)` | `evaluationRepository.deleteById(id)` |

### Aggregation Pipeline to Spring Data Query

| MongoDB Aggregation | Spring Data |
|---------------------|-------------|
| `$group` by category | `@Query` or QueryDSL `groupBy()` |
| `$avg`, `$sum`, `$min`, `$max` | `@Query` with JPQL aggregate functions |
| `$sort` | `Sort.by(...)` |
| `$match` | `Specification` or QueryDSL `where()` |

### Aggregation Example

```javascript
// Express: MongoDB aggregation
const stats = await Evaluation.aggregate([
  { $group: { _id: '$category', avgScore: { $avg: '$score' }, count: { $sum: 1 } } },
  { $sort: { avgScore: -1 } }
]);
```

```java
// Spring Boot: QueryDSL or @Query
@Query("""
    SELECT e.category, AVG(e.score), COUNT(e)
    FROM Evaluation e
    GROUP BY e.category
    ORDER BY AVG(e.score) DESC
    """)
List<Object[]> findStatsByCategory();
```

## DTO Pattern

### Structure

```java
// EvaluationDto.java
public interface EvaluationDto {

    interface Request {
        String title();
        Category category();
        Integer score();
        String evaluator();
        String evaluatee();
    }

    interface Response {
        String id();
        String title();
        String category();
        Integer score();
        String status();
        String evaluator();
        String evaluatee();
        LocalDateTime createdAt();
        LocalDateTime updatedAt();
    }
}
```

### Request/Response Records

```java
// EvaluationRequest.java
public record EvaluationRequest(
    @NotBlank String title,
    @NotNull Category category,
    @NotNull @Min(1) @Max(100) Integer score,
    @NotBlank String evaluator,
    @NotBlank String evaluatee
) {}

// EvaluationResponse.java
public record EvaluationResponse(
    String id,
    String title,
    String category,
    Integer score,
    String status,
    String evaluator,
    String evaluatee,
    LocalDateTime createdAt,
    LocalDateTime updatedAt
) {}
```

## MapStruct Mapper

```java
@Mapper(componentModel = "spring")
public interface EvaluationMapper {

    EvaluationMapper INSTANCE = Mappers.getMapper(EvaluationMapper.class);

    Evaluation toEntity(EvaluationRequest request);

    EvaluationResponse toResponse(Evaluation entity);

    PageResponse<EvaluationResponse> toPageResponse(Page<Evaluation> page);
}
```

## Common Patterns

### Pagination Response

```java
public record PageResponse<T>(
    List<T> data,
    int page,
    int size,
    long total,
    int totalPages
) {
    public static <T> PageResponse<T> of(List<T> data, Page<?> page) {
        return new PageResponse<>(
            data,
            page.getNumber() + 1,
            page.getSize(),
            page.getTotalElements(),
            page.getTotalPages()
        );
    }
}
```

### API Response Wrapper

```java
@Data
public class ApiResponse<T> {
    private boolean success;
    private T data;
    private String message;

    public static <T> ApiResponse<T> success(T data) {
        ApiResponse<T> response = new ApiResponse<>();
        response.success = true;
        response.data = data;
        return response;
    }

    public static <T> ApiResponse<T> error(String message) {
        ApiResponse<T> response = new ApiResponse<>();
        response.success = false;
        response.message = message;
        return response;
    }
}
```

### Exception Handling

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> handleValidation(MethodArgumentNotValidException ex) {
        String message = ex.getBindingResult().getFieldErrors().stream()
            .map(FieldError::getDefaultMessage)
            .collect(Collectors.joining(", "));
        return ResponseEntity.badRequest().body(ApiResponse.error(message));
    }

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ApiResponse<Void>> handleNotFound(ResourceNotFoundException ex) {
        return ResponseEntity.status(404).body(ApiResponse.error(ex.getMessage()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleGeneral(Exception ex) {
        return ResponseEntity.status(500).body(ApiResponse.error("서버 오류가 발생했습니다"));
    }
}
```

## Package Structure

```
feature/evaluation/
├── controller/
│   ├── EvaluationController.java
│   └── EvaluationControllerApiDoc.java
├── service/
│   ├── EvaluationService.java
│   └── impl/
│       └── EvaluationServiceImpl.java
├── mapper/
│   └── EvaluationMapper.java
├── dto/
│   └── EvaluationDto.java
├── repository/
│   ├── EvaluationRepository.java
│   ├── EvaluationQueryRepository.java
│   └── impl/
│       └── EvaluationRepositoryImpl.java
└── domain/
    └── Evaluation.java
```
