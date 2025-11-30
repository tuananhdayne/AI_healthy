import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { HealthProfile } from './firebase.service';
import { environment } from '../../environments/environment';

export interface BMIResult {
  value: number;
  category: 'hơi gầy' | 'cân đối' | 'hơi thừa cân' | 'thừa cân nhiều';
  description: string;
}

export interface ExerciseSuggestion {
  title: string;
  exercises: string[];
  frequency: string;
  duration: string;
  notes: string;
}

@Injectable({
  providedIn: 'root'
})
export class HealthProfileService {
  private readonly apiBaseUrl = this.normalizeBaseUrl(environment.apiBaseUrl);

  constructor(private http: HttpClient) {}

  private normalizeBaseUrl(url?: string): string {
    if (!url) {
      return window.location.origin;
    }
    if (url.startsWith('/')) {
      return `${window.location.origin}${url}`.replace(/\/$/, '');
    }
    return url.replace(/\/$/, '');
  }

  /**
   * Tính BMI từ chiều cao (cm) và cân nặng (kg)
   */
  calculateBMI(chieuCao: number, canNang: number): BMIResult {
    const heightInMeters = chieuCao / 100;
    const bmi = canNang / (heightInMeters * heightInMeters);
    
    let category: BMIResult['category'];
    let description: string;

    if (bmi < 18.5) {
      category = 'hơi gầy';
      description = 'BMI của bạn ở mức hơi thấp. Nên tăng cường dinh dưỡng và tập luyện để tăng cơ bắp.';
    } else if (bmi >= 18.5 && bmi < 25) {
      category = 'cân đối';
      description = 'BMI của bạn ở mức lý tưởng. Hãy duy trì chế độ ăn uống và tập luyện hiện tại.';
    } else if (bmi >= 25 && bmi < 30) {
      category = 'hơi thừa cân';
      description = 'BMI của bạn hơi cao. Nên kết hợp chế độ ăn uống lành mạnh và tập luyện thường xuyên.';
    } else {
      category = 'thừa cân nhiều';
      description = 'BMI của bạn ở mức cao. Nên tham khảo ý kiến chuyên gia dinh dưỡng và tăng cường vận động.';
    }

    return {
      value: Math.round(bmi * 10) / 10,
      category,
      description
    };
  }

  /**
   * Tạo gợi ý tập luyện bằng Gemini (AI) - rộng và linh hoạt hơn
   */
  async generateExerciseSuggestionWithAI(profile: HealthProfile, bmiResult: BMIResult): Promise<ExerciseSuggestion | null> {
    try {
      const response = await this.http.post<any>(
        `${this.apiBaseUrl}/api/health-profile/exercise-suggestion`,
        {
          tuoi: profile.tuoi,
          chieuCao: profile.chieuCao,
          canNang: profile.canNang,
          mucVanDong: profile.mucVanDong,
          gioiTinh: profile.gioiTinh,
          bmi: bmiResult.value,
          bmiCategory: bmiResult.category
        }
      ).toPromise();

      if (response && response.title) {
        // Đảm bảo exercises là array of strings
        let exercises: string[] = [];
        if (Array.isArray(response.exercises)) {
          exercises = response.exercises.map((ex: any, index: number) => {
            // Nếu là object, lấy text hoặc name hoặc title
            if (typeof ex === 'object' && ex !== null) {
              const text = ex.text || ex.name || ex.title || ex.description || ex.content;
              if (text) return String(text).trim();
              // Nếu không có field text, thử lấy giá trị đầu tiên
              const keys = Object.keys(ex);
              if (keys.length > 0) {
                return String(ex[keys[0]]).trim();
              }
              return `Bài tập ${index + 1}`;
            }
            // Nếu là string, trả về trực tiếp
            if (typeof ex === 'string') {
              return ex.trim();
            }
            // Nếu là number hoặc khác, convert sang string
            return String(ex).trim();
          }).filter((ex: string) => ex && ex.trim().length > 0 && ex !== 'null' && ex !== 'undefined');
        } else if (response.exercises) {
          // Nếu không phải array, thử convert
          if (typeof response.exercises === 'string') {
            exercises = [response.exercises.trim()];
          } else {
            exercises = [String(response.exercises).trim()];
          }
        }

        // Nếu không có exercises hợp lệ, return null để dùng fallback
        if (exercises.length === 0) {
          console.warn('⚠️ API trả về exercises rỗng hoặc không hợp lệ, dùng fallback');
          return null;
        }

        // Log để debug
        console.log('📋 Gemini trả về:', {
          title: response.title,
          exercisesCount: exercises.length,
          exercises: exercises.slice(0, 3) // Log 3 bài đầu
        });

        return {
          title: String(response.title || 'Kế hoạch tập luyện').trim(),
          exercises: exercises,
          frequency: String(response.frequency || '3-4 lần/tuần').trim(),
          duration: String(response.duration || '30-40 phút/buổi').trim(),
          notes: String(response.notes || '').trim()
        };
      }
      console.warn('⚠️ API không trả về title, dùng fallback');
      return null;
    } catch (error) {
      console.error('❌ Lỗi khi gọi API generate exercise suggestion:', error);
      return null;
    }
  }

  /**
   * Tạo gợi ý tập luyện dựa trên BMI, mức vận động và tuổi
   * Ưu tiên dùng Gemini để đa dạng, fallback về hardcode nếu lỗi
   */
  async generateExerciseSuggestion(profile: HealthProfile, bmiResult: BMIResult): Promise<ExerciseSuggestion> {
    // Ưu tiên dùng Gemini để có gợi ý đa dạng
    try {
      const aiSuggestion = await this.generateExerciseSuggestionWithAI(profile, bmiResult);
      if (aiSuggestion && aiSuggestion.exercises && aiSuggestion.exercises.length > 0) {
        // Validate exercises trước khi trả về
        const validExercises = aiSuggestion.exercises.filter(ex => ex && typeof ex === 'string' && ex.trim().length > 0);
        if (validExercises.length > 0) {
          console.log('✅ Đã tạo gợi ý tập luyện bằng Gemini với', validExercises.length, 'bài tập');
          return {
            ...aiSuggestion,
            exercises: validExercises
          };
        }
      }
      console.log('⚠️ Gemini không trả về kết quả hợp lệ, dùng fallback');
    } catch (error) {
      console.error('❌ Lỗi khi gọi Gemini:', error);
      console.log('⚠️ Chuyển sang dùng gợi ý mặc định (fallback)');
    }

    // Fallback về hardcode nếu Gemini lỗi hoặc không trả về kết quả hợp lệ
    console.log('✅ Sử dụng gợi ý tập luyện mặc định (hardcode)');
    return this.generateExerciseSuggestionFallback(profile, bmiResult);
  }

  /**
   * Fallback: Tạo gợi ý tập luyện hardcode (giữ nguyên logic cũ)
   */
  private generateExerciseSuggestionFallback(profile: HealthProfile, bmiResult: BMIResult): ExerciseSuggestion {
    const { tuoi, mucVanDong, chieuCao, canNang } = profile;
    const { category } = bmiResult;

    // Xác định cường độ tập luyện dựa trên tuổi
    const isElderly = tuoi >= 50;
    const isYoung = tuoi < 30;

    let title: string;
    let exercises: string[] = [];
    let frequency: string;
    let duration: string;
    let notes: string;

    // Gợi ý dựa trên BMI
    if (category === 'hơi gầy') {
      title = 'Tập luyện tăng cơ và sức khỏe';
      exercises = [
        'Đi bộ nhanh 20-30 phút',
        'Tập thể dục nhẹ nhàng (yoga, pilates)',
        'Tập tạ nhẹ hoặc bodyweight exercises',
        'Bơi lội (nếu có điều kiện)'
      ];
      frequency = '3-4 lần/tuần';
      duration = '20-30 phút/buổi';
      notes = 'Kết hợp với chế độ dinh dưỡng giàu protein để tăng cơ bắp.';
    } else if (category === 'cân đối') {
      title = 'Duy trì sức khỏe và thể lực';
      if (mucVanDong === 'it') {
        exercises = [
          'Đi bộ 30 phút mỗi ngày',
          'Tập thể dục nhẹ nhàng 2-3 lần/tuần',
          'Đạp xe hoặc bơi lội',
          'Yoga hoặc stretching'
        ];
        frequency = '3-4 lần/tuần';
        duration = '30-40 phút/buổi';
        notes = 'Bắt đầu từ từ và tăng dần cường độ.';
      } else if (mucVanDong === 'vua') {
        exercises = [
          'Chạy bộ hoặc đi bộ nhanh',
          'Tập thể dục toàn thân',
          'Đạp xe hoặc bơi lội',
          'Tập tạ vừa phải'
        ];
        frequency = '4-5 lần/tuần';
        duration = '40-50 phút/buổi';
        notes = 'Duy trì thói quen tập luyện hiện tại.';
      } else {
        exercises = [
          'Chạy bộ hoặc HIIT',
          'Tập tạ và thể dục toàn thân',
          'Bơi lội hoặc đạp xe',
          'Thể thao đối kháng (nếu thích)'
        ];
        frequency = '5-6 lần/tuần';
        duration = '45-60 phút/buổi';
        notes = 'Tuyệt vời! Hãy tiếp tục duy trì.';
      }
    } else if (category === 'hơi thừa cân') {
      title = 'Tập luyện giảm cân và tăng cường sức khỏe';
      exercises = [
        'Đi bộ nhanh hoặc chạy bộ nhẹ',
        'Tập cardio (nhảy dây, aerobic)',
        'Tập thể dục toàn thân',
        'Đạp xe hoặc bơi lội'
      ];
      frequency = '4-5 lần/tuần';
      duration = '40-50 phút/buổi';
      notes = 'Kết hợp với chế độ ăn uống cân bằng để đạt hiệu quả tốt nhất.';
    } else {
      // thừa cân nhiều
      title = 'Tập luyện an toàn để cải thiện sức khỏe';
      exercises = [
        'Đi bộ chậm, tăng dần tốc độ',
        'Tập thể dục nhẹ nhàng tại nhà',
        'Yoga hoặc stretching',
        'Bơi lội (nếu có điều kiện)'
      ];
      frequency = '3-4 lần/tuần';
      duration = '20-30 phút/buổi';
      notes = 'Bắt đầu từ từ, tăng dần cường độ. Nên tham khảo ý kiến bác sĩ trước khi bắt đầu.';
    }

    // Điều chỉnh theo tuổi
    if (isElderly) {
      exercises = exercises.map(ex => ex.replace(/chạy bộ|HIIT|tập tạ nặng/gi, 'đi bộ hoặc tập nhẹ'));
      frequency = '3-4 lần/tuần';
      duration = '20-30 phút/buổi';
      notes += ' Lưu ý: Tập luyện nhẹ nhàng, phù hợp với tuổi tác.';
    } else if (!isYoung && category !== 'cân đối') {
      notes += ' Lưu ý: Khởi động kỹ trước khi tập và nghỉ ngơi đầy đủ.';
    }

    return {
      title,
      exercises,
      frequency,
      duration,
      notes
    };
  }

  /**
   * Tạo context string cho chatbot (async version)
   */
  async createChatbotContext(profile: HealthProfile, bmiResult: BMIResult): Promise<string> {
    const suggestion = await this.generateExerciseSuggestion(profile, bmiResult);
    
    return `[PROFILE]
Tuổi: ${profile.tuoi}
Giới tính: ${this.getGioiTinhLabel(profile.gioiTinh)}
Chiều cao: ${profile.chieuCao} cm
Cân nặng: ${profile.canNang} kg
Mức vận động: ${this.getMucVanDongLabel(profile.mucVanDong)}
BMI: ${bmiResult.value} (${bmiResult.category})
[/PROFILE]

Dựa vào hồ sơ trên, hãy đưa ra gợi ý tập luyện nhẹ, an toàn, dễ thực hiện phù hợp với:
- BMI: ${bmiResult.category} (${bmiResult.value})
- Giới tính: ${this.getGioiTinhLabel(profile.gioiTinh)}
- Mức vận động hiện tại: ${this.getMucVanDongLabel(profile.mucVanDong)}
- Tuổi: ${profile.tuoi}

Gợi ý tập luyện tham khảo:
- ${suggestion.title}
- Tần suất: ${suggestion.frequency}
- Thời gian: ${suggestion.duration}
- Các bài tập: ${suggestion.exercises.join(', ')}

Lưu ý: ${suggestion.notes}

QUAN TRỌNG: Không được chẩn đoán bệnh, không được gợi ý thuốc. Chỉ đưa ra lời khuyên tập luyện và lối sống nhẹ nhàng, an toàn.`;
  }

  /**
   * Tạo context string cho chatbot (sync version - dùng fallback)
   */
  createChatbotContextSync(profile: HealthProfile, bmiResult: BMIResult): string {
    const suggestion = this.generateExerciseSuggestionFallback(profile, bmiResult);
    
    return `[PROFILE]
Tuổi: ${profile.tuoi}
Giới tính: ${this.getGioiTinhLabel(profile.gioiTinh)}
Chiều cao: ${profile.chieuCao} cm
Cân nặng: ${profile.canNang} kg
Mức vận động: ${this.getMucVanDongLabel(profile.mucVanDong)}
BMI: ${bmiResult.value} (${bmiResult.category})
[/PROFILE]

Dựa vào hồ sơ trên, hãy đưa ra gợi ý tập luyện nhẹ, an toàn, dễ thực hiện phù hợp với:
- BMI: ${bmiResult.category} (${bmiResult.value})
- Giới tính: ${this.getGioiTinhLabel(profile.gioiTinh)}
- Mức vận động hiện tại: ${this.getMucVanDongLabel(profile.mucVanDong)}
- Tuổi: ${profile.tuoi}

Gợi ý tập luyện tham khảo:
- ${suggestion.title}
- Tần suất: ${suggestion.frequency}
- Thời gian: ${suggestion.duration}
- Các bài tập: ${suggestion.exercises.join(', ')}

Lưu ý: ${suggestion.notes}

QUAN TRỌNG: Không được chẩn đoán bệnh, không được gợi ý thuốc. Chỉ đưa ra lời khuyên tập luyện và lối sống nhẹ nhàng, an toàn.`;
  }

  /**
   * Chuyển đổi mức vận động sang label
   */
  getMucVanDongLabel(mucVanDong: 'it' | 'vua' | 'nhieu'): string {
    const labels = {
      'it': 'Ít',
      'vua': 'Vừa',
      'nhieu': 'Nhiều'
    };
    return labels[mucVanDong] || mucVanDong;
  }

  /**
   * Chuyển đổi giới tính sang label
   */
  getGioiTinhLabel(gioiTinh: 'nam' | 'nu' | 'khac'): string {
    const labels = {
      'nam': 'Nam',
      'nu': 'Nữ',
      'khac': 'Khác'
    };
    return labels[gioiTinh] || gioiTinh;
  }
}

