import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MissPassComponent } from './miss-pass.component';

describe('MissPassComponent', () => {
  let component: MissPassComponent;
  let fixture: ComponentFixture<MissPassComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ MissPassComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MissPassComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
